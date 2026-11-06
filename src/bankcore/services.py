"""Core transfer semantics: atomic ledger, balance projection, idempotency, and outbox."""
import hashlib
import json
import uuid
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from bankcore.database import TREASURY_ID
from bankcore.models import Account, Transfer, LedgerEntry, IdempotencyRecord, OutboxEvent
from bankcore.schemas import TransferRequest, FundingRequest

REVIEW_THRESHOLD_CENTS = 1_000_000

def _fingerprint(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def _existing(db: Session, key: str, endpoint: str, payload: dict) -> dict | None:
    record = db.get(IdempotencyRecord, key)
    if record:
        if record.endpoint != endpoint or record.fingerprint != _fingerprint(payload):
            raise HTTPException(409, "Idempotency-Key was already used for another request")
        return json.loads(record.response_json)
    return None

def _reserve_key(db: Session, key: str, endpoint: str, payload: dict, response: dict):
    db.add(IdempotencyRecord(key=key, endpoint=endpoint, fingerprint=_fingerprint(payload),
                             response_json=json.dumps(response, sort_keys=True)))

def _get_accounts_locked(db: Session, source_id: str, destination_id: str):
    ids = sorted([source_id, destination_id])
    accounts = db.scalars(select(Account).where(Account.id.in_(ids)).order_by(Account.id).with_for_update()).all()
    by_id = {a.id: a for a in accounts}
    if len(by_id) != 2:
        raise HTTPException(404, "One or both accounts not found")
    if any(a.status != "ACTIVE" for a in accounts):
        raise HTTPException(409, "Frozen accounts cannot send or receive transfers")
    if any(a.currency != "USD" for a in accounts):
        raise HTTPException(422, "Only USD is supported")
    return by_id[source_id], by_id[destination_id]

def create_account(db: Session, owner_label: str, currency: str) -> dict:
    account = Account(id=str(uuid.uuid4()), owner_label=owner_label, currency=currency,
                      balance_minor=0, status="ACTIVE")
    db.add(account)
    db.flush()
    return {"id": account.id, "owner_label": account.owner_label, "currency": account.currency,
            "balance_minor": 0, "status": account.status}

def _apply_transfer(db: Session, *, source_id: str, destination_id: str,
                    amount: int, reference: str, kind: str, key: str, endpoint: str, payload: dict) -> dict:
    cached = _existing(db, key, endpoint, payload)
    if cached is not None:
        return cached
    if source_id == destination_id:
        raise HTTPException(422, "Cannot transfer to the same account")
    if destination_id == TREASURY_ID:
        raise HTTPException(422, "Transfers to demo treasury are not supported")
    if kind == "TRANSFER" and source_id == TREASURY_ID:
        raise HTTPException(422, "Direct transfer from treasury is not supported")
    source, destination = _get_accounts_locked(db, source_id, destination_id)
    if source.balance_minor < amount:
        raise HTTPException(409, "Insufficient funds")
    review = kind == "TRANSFER" and amount >= REVIEW_THRESHOLD_CENTS
    transfer = Transfer(id=str(uuid.uuid4()), source_account_id=source.id,
                        destination_account_id=destination.id, amount_minor=amount,
                        status="REVIEW_REQUIRED" if review else "POSTED", kind=kind, reference=reference)
    db.add(transfer)
    if not review:
        source.balance_minor -= amount
        destination.balance_minor += amount
        db.add_all([LedgerEntry(id=str(uuid.uuid4()), transfer_id=transfer.id,
                                account_id=source.id, amount_minor=-amount),
                    LedgerEntry(id=str(uuid.uuid4()), transfer_id=transfer.id,
                                account_id=destination.id, amount_minor=amount)])
    response = {"id": transfer.id, "source_account_id": source.id,
                "destination_account_id": destination.id, "amount_minor": amount,
                "status": transfer.status, "kind": kind, "reference": reference}
    event_type = "transfer.review_requested" if review else "transfer.posted"
    db.add(OutboxEvent(id=str(uuid.uuid4()), event_type=event_type,
                       payload_json=json.dumps(response, sort_keys=True), state="PENDING"))
    _reserve_key(db, key, endpoint, payload, response)
    db.flush()
    return response

def post_transfer(db: Session, request: TransferRequest, key: str):
    payload = request.model_dump()
    return _apply_transfer(db, source_id=request.source_account_id,
                           destination_id=request.destination_account_id, amount=request.amount_minor,
                           reference=request.reference, kind="TRANSFER", key=key,
                           endpoint="/v1/transfers", payload=payload)

def demo_fund(db: Session, request: FundingRequest, key: str):
    payload = request.model_dump()
    return _apply_transfer(db, source_id=TREASURY_ID, destination_id=request.account_id,
                           amount=request.amount_minor, reference="Synthetic opening funds",
                           kind="DEMO_FUND", key=key, endpoint="/v1/demo/fund", payload=payload)
