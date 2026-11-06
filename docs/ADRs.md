# Architecture decision records

## ADR-001 — Modular monolith first (accepted)

**Context:** Microservice boundaries introduce network hops, stale state and distributed transaction complexity. A transfer requires indivisible debit and credit.

**Decision:** Put balances, transfer state, ledger and outbox into one SQL transaction, with code split into testable modules. Keep delivery and analytics asynchronous.

**Alternatives:** Multiple independently writing account services; coordinated saga for same-bank payment. **Rejected for v0.1**: high consistency complexity and no benefit for a small demonstration.

**Consequence:** Simpler correctness and free local tests; independent scaling requires future redesign.

## ADR-002 — Relational ACID store over NoSQL for ledger authority (accepted)

**Decision:** SQLAlchemy + SQLite locally, PostgreSQL as an optional future runtime. Row locking / writer serialization for concurrent debits. Use integer cents.

**Rejected:** Redis as primary ledger (cache consistency) and eventually consistent NoSQL account balance writes (more complex invariants).

**Consequence:** Single primary write bottleneck; bank-critical integrity is easier to reason about.

## ADR-003 — Double-entry append-only ledger (accepted, with demo caveat)

**Decision:** Every posted transfer generates one debit and one credit. Balances are cached projections updated inside the same DB transaction.

**Caveat:** The educational treasury's initial synthetic capital is a genesis seed not recorded as a complete equity journal. In production, record *every* opening balance and issuance via appropriate accounts and transactions; harden append-only enforcement in DB.

## ADR-004 — Transactional outbox instead of direct publish (accepted)

**Decision:** Insert outbox record in same transaction as transfer. Worker polls committed events. Never publish events before the transfer commits. Worker/consumers must tolerate duplicates.

**Consequence:** Eventual notification delivery, polling overhead, backlogs possible; need retries, DLQ, monitoring and a real broker in the next phase. Local mock broker uses same DB and **does not establish distributed Kafka delivery semantics**.

## ADR-005 — Client idempotency keys (accepted)

**Decision:** Require Idempotency-Key for money-moving API; hash canonical request; persist response in transaction. Identical retried request returns same transfer. Conflicting reuse yields 409.

**Consequence:** Storage growth and key-lifecycle policy; initial version proves key replay in SQLite only. PostgreSQL same-key concurrency requires more work.

## ADR-006 — Reject or review risky transfers before posting (accepted)

**Decision:** A fixed >= $10k threshold generates a `REVIEW_REQUIRED` transfer with no ledger writes, plus outbox alert.

**Consequence:** Illustrative safety decision, not legitimate fraud scoring, no manual approval implementation. Integrating FraudShield would require explicit policy versioning and fraud score provenance.

## ADR-007 — No Redis cache for authorization of funds (accepted)

**Decision:** Never approve debit using a cached account balance. Later use read-model caches only for browsing and statements, with caveats around staleness.

**Consequence:** Source-of-truth SQL reads incur transactional cost but prevent stale-balance overspend.