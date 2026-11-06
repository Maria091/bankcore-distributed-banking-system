"""Checks ledger conservation against artificial genesis and cached account projections.

This is an operational verification helper, not an external financial audit.
"""
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.orm import Session
from bankcore.database import DEMO_TREASURY_CENTS, TREASURY_ID
from bankcore.models import Account, Transfer, LedgerEntry, OutboxEvent

def verify_ledger(db: Session) -> dict:
    accounts = {a.id: a for a in db.scalars(select(Account)).all()}
    transfers = db.scalars(select(Transfer)).all()
    all_entries = db.scalars(select(LedgerEntry)).all()
    errors = []
    by_transfer = defaultdict(list)
    by_account = defaultdict(int)
    for e in all_entries:
        by_transfer[e.transfer_id].append(e)
        by_account[e.account_id] += e.amount_minor
    for t in transfers:
        entries = by_transfer[t.id]
        if t.status == "REVIEW_REQUIRED":
            if entries:
                errors.append(f"Review transfer {t.id} unexpectedly has ledger entries")
            continue
        if len(entries) != 2:
            errors.append(f"Posted transfer {t.id} has {len(entries)} entries, expected 2")
            continue
        actual = {(e.account_id, e.amount_minor) for e in entries}
        expected = {(t.source_account_id, -t.amount_minor), (t.destination_account_id, t.amount_minor)}
        if actual != expected:
            errors.append(f"Transfer {t.id} debit/credit mismatch")
    transfer_ids = {t.id for t in transfers}
    for transfer_id in by_transfer:
        if transfer_id not in transfer_ids:
            errors.append(f"Orphan ledger entries {transfer_id}")
    for aid, account in accounts.items():
        genesis = DEMO_TREASURY_CENTS if aid == TREASURY_ID else 0
        if account.balance_minor != genesis + by_account[aid]:
            errors.append(f"Balance projection mismatch for account {aid}")
    if sum(a.balance_minor for a in accounts.values()) != DEMO_TREASURY_CENTS:
        errors.append("Total synthetic balances differ from initial treasury seed")
    if len(db.scalars(select(OutboxEvent)).all()) != len(transfers):
        errors.append("Outbox event count != transfer count")
    return {"ok": not errors, "checked_accounts": len(accounts),
            "checked_transfers": len(transfers), "errors": errors}
