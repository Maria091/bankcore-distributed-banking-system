# Threat model and boundaries

**WARNING:** This educational project does not implement a secure bank. It must not be exposed to real users or public networks.

## Protected assets

Simulated balances, ledger integrity, event ordering, audit records and the ability to issue transfer requests.

## Main threats

| Threat | Local demo mitigation | Mandatory production controls |
|---|---|---|
| Unauthorized transfers | Shared demo API key | OAuth/OIDC identity, account ownership ACLs, token scopes, mTLS, bank controls |
| Replayed/malicious transfers | Idempotency key + request fingerprint | Principal-scoped key, expiry, abuse detection, replay monitoring |
| Concurrent overdraft | SQLite serial transaction; PG row locks in code | PG contention tests, deadlock handling, monitoring |
| Event loss | Outbox write shares DB commit | Durable broker, retry/backoff, DLQ, CDC and alerts |
| Sensitive data leakage | Synthetic account labels only; local bind default | Encryption, KMS, secret manager, redaction, access/audit controls |
| API abuse | Only local demo limits, strict amount validation | Per-principal quotas/rate limits, WAF, anti-fraud controls |
| Insider ledger tampering | ORM conventions only | Append-only DB permissions, tamper-evident journal, reconciliation |
| Exposure of example key | Demo key intentionally public | Managed secrets and key rotation; never use demo key on public hosts |

**Never commit passwords, real customer information, API tokens, payment card data or production transactions.** The Docker Compose example credentials are intentionally insecure development defaults and are not suitable for real services.
