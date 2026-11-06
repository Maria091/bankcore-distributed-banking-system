import pytest
from fastapi.testclient import TestClient
from bankcore.api import create_app

@pytest.fixture
def environment(tmp_path):
    url = f"sqlite:///{tmp_path / 'bankcore-test.db'}"
    app = create_app(url)
    with TestClient(app) as client:
        yield (client, url, app)
    app.state.engine.dispose()

@pytest.fixture
def client(environment):
    return environment[0]

@pytest.fixture
def headers():
    return {"X-API-Key": "local-demo-key-only"}

@pytest.fixture
def account(client, headers):
    def _create(name):
        response = client.post("/v1/accounts", json={"owner_label": name}, headers=headers)
        assert response.status_code == 201, response.text
        return response.json()["id"]
    return _create

@pytest.fixture
def funded(account, client, headers):
    a, b = account("Alice"), account("Bob")
    response = client.post("/v1/demo/fund", json={"account_id": a, "amount_minor": 50000},
                           headers={**headers, "Idempotency-Key": "fund-00000001"})
    assert response.status_code == 201, response.text
    return a, b
