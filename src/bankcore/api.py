"""HTTP surface: local-only demo, no real banking credentials or network access."""
import os
from fastapi import FastAPI, Depends, Header, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker, Session
from bankcore.database import make_engine, init_database, TREASURY_ID
from bankcore.models import Account, Transfer, LedgerEntry
from bankcore.schemas import AccountCreate, AccountOut, FundingRequest, TransferRequest, TransferOut, LedgerEntryOut
from bankcore.services import create_account, post_transfer, demo_fund
from bankcore.messaging import counts

DEMO_KEY = "local-demo-key-only"

def create_app(db_url: str | None = None):
    engine = make_engine(db_url)
    init_database(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    app = FastAPI(title="BankCore — Distributed Banking Design Simulator", version="0.1.0",
                  description="Synthetic money only. Do not use for real payments or expose publicly.")
    app.state.engine = engine
    app.state.SessionLocal = SessionLocal

    def session():
        with SessionLocal() as db:
            yield db

    def require_key(x_api_key: str = Header(default="")):
        expected = os.getenv("BANKCORE_DEMO_API_KEY", DEMO_KEY)
        if x_api_key != expected:
            raise HTTPException(401, "Invalid demo API key")

    def idem(idempotency_key: str = Header(default="", alias="Idempotency-Key")):
        if not (8 <= len(idempotency_key) <= 128) or any(c.isspace() for c in idempotency_key):
            raise HTTPException(400, "Idempotency-Key must be 8-128 non-whitespace characters")
        return idempotency_key

    @app.get("/health/live")
    def live(): return {"status": "ok"}

    @app.get("/health/ready", dependencies=[Depends(require_key)])
    def ready(db: Session = Depends(session)):
        return {"status": "ok" if db.get(Account, TREASURY_ID) is not None else "not_ready"}

    @app.post("/v1/accounts", response_model=AccountOut, status_code=201, dependencies=[Depends(require_key)])
    def accounts_create(body: AccountCreate, db: Session = Depends(session)):
        with db.begin():
            return create_account(db, body.owner_label, body.currency)

    @app.get("/v1/accounts/{account_id}", response_model=AccountOut, dependencies=[Depends(require_key)])
    def accounts_get(account_id: str, db: Session = Depends(session)):
        account = db.get(Account, account_id)
        if account is None or account.id == TREASURY_ID:
            raise HTTPException(404, "Account not found")
        return account

    @app.get("/v1/accounts/{account_id}/ledger", response_model=list[LedgerEntryOut], dependencies=[Depends(require_key)])
    def ledger(account_id: str, limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(session)):
        if db.get(Account, account_id) is None or account_id == TREASURY_ID:
            raise HTTPException(404, "Account not found")
        return db.scalars(select(LedgerEntry).where(LedgerEntry.account_id == account_id)
                          .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc()).limit(limit)).all()

    @app.post("/v1/demo/fund", response_model=TransferOut, status_code=201, dependencies=[Depends(require_key)])
    def fund(body: FundingRequest, key: str = Depends(idem), db: Session = Depends(session)):
        with db.begin():
            return demo_fund(db, body, key)

    @app.post("/v1/transfers", response_model=TransferOut, status_code=201, dependencies=[Depends(require_key)])
    def transfer(body: TransferRequest, key: str = Depends(idem), db: Session = Depends(session)):
        with db.begin():
            return post_transfer(db, body, key)

    @app.get("/v1/transfers/{transfer_id}", response_model=TransferOut, dependencies=[Depends(require_key)])
    def transfer_get(transfer_id: str, db: Session = Depends(session)):
        t = db.get(Transfer, transfer_id)
        if t is None: raise HTTPException(404, "Transfer not found")
        return t

    @app.get("/v1/ops/stats", dependencies=[Depends(require_key)])
    def stats(db: Session = Depends(session)):
        return {"ledger_entries": db.scalar(select(func.count()).select_from(LedgerEntry)), **counts(db)}

    return app

app = create_app()
