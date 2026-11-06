"""Run simulated transfer with a temporary SQLite DB; no real bank involved."""
import tempfile
import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from bankcore.api import create_app
from bankcore.worker import run_once

with tempfile.TemporaryDirectory() as directory:
    db_url = f"sqlite:///{Path(directory) / 'demo.db'}"
    app = create_app(db_url)
    with TestClient(app) as client:
        headers = {"X-API-Key": "local-demo-key-only"}
        def create(name):
            response = client.post("/v1/accounts", json={"owner_label": name}, headers=headers)
            response.raise_for_status()
            return response.json()["id"]
        alice, bob = create("Demo Alice"), create("Demo Bob")
        funding = client.post("/v1/demo/fund", json={"account_id": alice, "amount_minor": 20000},
                              headers={**headers, "Idempotency-Key": str(uuid.uuid4())})
        funding.raise_for_status()
        transfer = client.post("/v1/transfers", json={"source_account_id": alice,
                                 "destination_account_id": bob, "amount_minor": 7500,
                                 "reference": "Synthetic rent split"},
                               headers={**headers, "Idempotency-Key": str(uuid.uuid4())})
        transfer.raise_for_status()
        print("Transfer:", transfer.json())
        print("Balances (cents):", {"alice": client.get(f"/v1/accounts/{alice}", headers=headers).json()["balance_minor"],
                                   "bob": client.get(f"/v1/accounts/{bob}", headers=headers).json()["balance_minor"]})
        print("Worker:", run_once(db_url))
