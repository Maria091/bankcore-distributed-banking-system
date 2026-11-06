"""Database setup. SQLite dev mode serializes transactions; PostgreSQL is a documented optional path."""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

TREASURY_ID = "00000000-0000-0000-0000-000000000001"
DEMO_TREASURY_CENTS = 100_000_000

class Base(DeclarativeBase):
    pass

def make_engine(url: str | None = None):
    url = url or os.getenv("BANKCORE_DATABASE_URL", "sqlite:///./bankcore-local.db")
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False, "timeout": 30}
    engine = create_engine(url, **options)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "begin")
        def start_immediate(conn):
            conn.exec_driver_sql("BEGIN IMMEDIATE")
    return engine

def init_database(engine):
    from bankcore.models import Account
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)
    with Session.begin() as db:
        if db.get(Account, TREASURY_ID) is None:
            db.add(Account(id=TREASURY_ID, owner_label="DEMO TREASURY", currency="USD",
                           balance_minor=DEMO_TREASURY_CENTS, status="ACTIVE"))
