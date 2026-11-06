# BankCore: system design interview walkthrough

## 30-second project story

"I built a synthetic banking transfer simulator with FastAPI, SQLAlchemy, SQLite and a double-entry ledger. A transfer updates balances and appends two opposing ledger entries in one transaction. I added request idempotency to prevent duplicate debits, a transactional outbox for reliable event publication, a mock broker and an idempotent notification consumer. I verified critical invariants through API, concurrency, and reconciliation tests. I designed a PostgreSQL/Kafka scale-out architecture but have not deployed those components yet."

## Walk the whiteboard

1. Requirements and non-goals — transfer between synthetic USD accounts; real settlements/KYC out of scope.
2. Source of truth — PostgreSQL recommended, same-bank debits and credits in one SQL transaction.
3. Ledger — immutable double-entry records, integer cents and a cached balance projection.
4. Idempotency — per-request token, canonical hash, transactional response replay.
5. Concurrency — lock accounts in stable ID order and verify sufficient funds while locked.
6. Events — outbox in same commit, async relay + idempotent downstream consumers.
7. Failure injection — rollback, API retry, pending outbox retry and consumer deduplication.
8. Scale — partitioned ledger history, read replicas, async projections, telemetry and SLO-driven capacity tests.

## Questions interviewers may ask

**Why not use microservices for debiting and crediting?** One authoritative atomic database transaction is vastly simpler for same-bank transfers. We can distribute independent reads, analytics, notifications and fraud detection while retaining a single ledger authority.

**How do you prevent double-spending?** Protect balance check and debit/credit with transactional locking, plus transaction-level idempotency to handle retries. SQLite in this build uses serialized transactions; Postgres lock semantics are in design and must be integration-tested.

**Does Kafka guarantee exactly-once bank transfers?** No. Kafka messaging semantics don't automatically provide exactly-once external side effects. The ledger idempotency token and consumer inbox guarantee the intended *business effect* is not repeated, under the chosen failure model.

**What if the API succeeds but the response is lost?** Client retries using the same idempotency key. The server finds the recorded request fingerprint and returns the same saved transfer response.

**What if the service crashes after DB commit but before Kafka publish?** The outbox record survives and a relay retries it. Publication may be duplicated; consumers dedupe using event ID.

**What if the fraud service is unavailable?** Define a fail-open/fail-closed policy based on risk and product, with timeouts, circuit breaking and review queues. V0.1 has only a deterministic threshold before booking and no external dependency.

**What is eventually consistent?** Notifications, analytics and read projections may lag the transaction. Balance authorization must use the primary ledger, not a potentially stale cache.

**How would you integrate FraudShield AI?** Add a versioned risk adapter before the ledger commit with strict timeouts and an audit trail of model score, version and decision. Use asynchronous fraud analytics after transfer for monitoring, without suggesting a post-hoc score prevented an already settled payment.

## Trade-offs acknowledged

- Strong ledger consistency can constrain write throughput; eventual analytics cannot control debit authorization.
- SQLite is free/easy but not horizontally scalable and not sufficient for real concurrent load; Postgres is the target upgrade.
- In-DB mock broker is deterministic and testable, but not durable independent messaging or Kafka.
- Seeded treasury genesis makes local demo convenient but is not a complete accounting representation of issuance.