# Build verification — v0.1 local

Run date: 2026-11-06. Environment: container Python with FastAPI, SQLAlchemy, Pydantic, HTTPX, pytest preinstalled. Pip editable install was not available here because this environment has no external package index access; tests were executed with PYTHONPATH=src instead.

Command: `PYTHONPATH=src pytest -q`

Result: **18 passed in 3.03s**.

Command: `PYTHONPATH=src python scripts/demo.py`

Result: Created two synthetic accounts, funded demo Alice with 20000 cents, transferred 7500 cents to Bob, leaving Alice with 12500 cents and Bob with 7500 cents. The one-shot worker dispatched 2 outbox events and created 2 idempotent mock notifications; 0 events remained pending.

Command: `PYTHONPATH=src python -m compileall -q src scripts tests`

Result: Completed with no reported errors.

Notes: Docker/Postgres, Kafka, cloud environments, security hardening, and real-money payments were NOT executed or tested. Benchmark SLO targets are design exercises, not actual measurements.
