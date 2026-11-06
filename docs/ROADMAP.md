# BankCore delivery milestones

## Phase 1 — Working local foundation (v0.1)

- [x] Architecture and database design, API contracts, trade-offs and threat model.
- [x] Synthetic USD account creation and seeded treasury for demo funding.
- [x] Idempotent transfers, double-entry bookkeeping, strict integer amounts.
- [x] Rule-based review hold before ledger posting.
- [x] Transactional outbox, in-database mock broker, inbox deduplication.
- [x] FastAPI app, OpenAPI, tests, demonstration script, reconciliation CLI and CI workflow configuration.

## Phase 2 — PostgreSQL hardening (free Docker)

- [ ] Run/verify Compose with Postgres; integrate Alembic migrations.
- [ ] Postgres same-idempotency-key concurrency locking/retry handling.
- [ ] Database-enforced ledger immutability and reconciler, accurate opening equity journal.
- [ ] PostgreSQL integration tests with competing requests and fault injection.

## Phase 3 — Distributed event system (local Docker)

- [ ] Redpanda/Kafka and outbox publisher with retry/backoff and DLQ.
- [ ] Separate notification service with persistent inbox; duplicate/reordering/recovery tests.
- [ ] OpenTelemetry tracing across worker and API; Prometheus metrics and Grafana dashboards.
- [ ] Optional FraudShield AI policy adapter: risk scoring before money movement (synthetic only).

## Phase 4 — Scale and portfolio demonstration

- [ ] AuthN/AuthZ simulator with principal ownership, contract tests and security review.
- [ ] k6/Locust load tests; publish real measurements, bottlenecks and benchmark environment.
- [ ] Read models, cache and replicas, data partitioning decisions and capacity reports.
- [ ] Screencast, architecture review, multi-stage GitHub release and LinkedIn portfolio write-up.

## Budget

Local SQLite uses Python packages and zero cloud spend. Docker Postgres/Kafka use local compute only. No Azure or AWS resources have been provisioned by this project. Monitor any future cloud provisioned resources and require explicit approval before billing.
