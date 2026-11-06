# BankCore HTTP API v0.1

Base URL: `http://127.0.0.1:8000` (local only). JSON only. 

**Headers:** `X-API-Key: local-demo-key-only` required except liveness. Write endpoints for demo funding and transfers additionally require `Idempotency-Key` (8–128 non-whitespace chars). Keys represent a logically unique request and should be reused on client retries.

This is a **demo shared key, not real authentication**, and provides no tenant or account ownership authorization.

## Resource endpoints

| Verb | Path | Request | Success response |
|---|---|---|---|
| GET | `/health/live` | — | `200 {"status":"ok"}` |
| GET | `/health/ready` | API key | `200 {"status":"ok"}` |
| POST | `/v1/accounts` | `{"owner_label":"Demo Alice","currency":"USD"}` | `201 AccountOut` |
| GET | `/v1/accounts/{account_id}` | — | `200 AccountOut` |
| GET | `/v1/accounts/{account_id}/ledger?limit=50` | — | `200 LedgerEntryOut[]` |
| POST | `/v1/demo/fund` | `{"account_id":"uuid","amount_minor":20000}` | `201 TransferOut` |
| POST | `/v1/transfers` | `TransferRequest` | `201 TransferOut` |
| GET | `/v1/transfers/{transfer_id}` | — | `200 TransferOut` |
| GET | `/v1/ops/stats` | API key | `200` counts |

### Sample transfer request

```http
POST /v1/transfers HTTP/1.1
Host: 127.0.0.1:8000
X-API-Key: local-demo-key-only
Idempotency-Key: transfer-2026-000001
Content-Type: application/json

{"source_account_id":"<uuid>","destination_account_id":"<uuid>","amount_minor":7500,"reference":"synthetic rent split"}
```

### Success

```json
{"id":"<transfer-id>","source_account_id":"<uuid>","destination_account_id":"<uuid>","amount_minor":7500,"status":"POSTED","kind":"TRANSFER","reference":"synthetic rent split"}
```

### Review response

Same response shape but `status: REVIEW_REQUIRED`; the balances do not change and no ledger entries are created. Amounts of >= `1000000` cents ($10,000) are put into review by a simple fixed threshold.

### Error contract

FastAPI/Pydantic default `detail` response. Common statuses:

- `400` idempotency key missing/malformed.
- `401` demo key missing/invalid.
- `404` account or transfer not found.
- `409` insufficient balance, idempotency conflict or frozen account.
- `422` invalid request, same-account transfer, unsupported currency/treasury misuse.

`amount_minor` is a strictly validated integer, positive and within maximums (`<= 10,000,000` for transfers; `<= 5,000,000` for demo funding). No floating-point dollars or real currencies outside USD.

## Retry protocol

A client must generate and persist a unique idempotency key before the first request. On HTTP timeout, retry **exactly the same payload and key**. The server returns the same transfer body without additional ledger entries. Reusing the same key with different payload or endpoint returns 409. No timestamp expiry is currently implemented, so records persist indefinitely in the local database.

## Schema

The automatically generated OpenAPI schema is in [`openapi.json`](openapi.json) and accessible at `/openapi.json` when the app runs.