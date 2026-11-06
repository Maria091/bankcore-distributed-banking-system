# Testing and verification plan

## Executed locally for v0.1

Run `PYTHONPATH=src pytest -q` without installation if the required Python dependencies are already present; or `pip install -e '.[dev]' && pytest -q` on a connected developer machine.

The suite verifies:

- API health, shared local key requirement, account creation and reads.
- Valid transfer changes two balances and returns queryable transfer and ledger entries.
- Strict positive integer amount validation; account/treasury misuse prevention.
- Same idempotency key + identical request -> same transfer; changed payload/route -> 409.
- Overdraft and failed transaction do not create ledger or outbox side effects.
- Review threshold does not debit accounts.
- Each posted transfer creates exactly two entries whose sum is zero.
- Aggregate simulated account balances remain equal to initial treasury seed (conservation).
- Standalone ledger reconciler detects tampered balances, checks per-account projections and per-transfer postings.
- Outbox dispatch to local mock broker and notification processing are idempotent.
- Concurrent competing debits cannot overdraw (SQLite serialized local transaction).

The API suite does **not** prove that PostgreSQL, Kafka, cloud deployment, identity service, or load-test SLOs have passed. Add dedicated integration tests before such claims.

## Next stage quality gates

| Test | Target / acceptance criterion | Stage |
|---|---|---|
| PostgreSQL concurrent same-key transfer | One transfer posted, identical response replayed, no 500s | v0.2 |
| PostgreSQL overdraft contention | Only available funds transferable under multiple API replicas | v0.2 |
| Postgres durability restart | Every acknowledged transfer survives DB restart | v0.2 |
| Outbox crash after event publish | Worker recovery causes no duplicate business effect | v0.3 |
| Kafka duplicate/reorder/partition | Inbox or idempotent consumer correct, replay procedures documented | v0.3 |
| Failure injection / DLQ | Backoff and operator alerts work | v0.3 |
| k6 or Locust load | Measure p50/p95/p99 response, successful TPS, max DB lock wait | v0.4 |
| Recover from backups | Ledger and balances consistent after PITR | v0.4 |
| Pen-test controls | OIDC scopes, account authorization, request/PII logging controls | later |

## Reference invariants

For every posted transfer `t`:

```text
count(entries where transfer_id=t) == 2
sum(entry.amount_minor where transfer_id=t) == 0
source_entry == -t.amount_minor
destination_entry == +t.amount_minor
```

For every reviewed transfer, no entry and no balance delta. For every committed transfer, one outbox event and one idempotency response. **Never report load/performance numbers without reproducible benchmark evidence.**