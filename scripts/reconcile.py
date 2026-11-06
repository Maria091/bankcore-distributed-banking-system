"""Exit non-zero if any transfer / balance / outbox invariant is violated."""
import json
from sqlalchemy.orm import sessionmaker
from bankcore.database import make_engine, init_database
from bankcore.reconcile import verify_ledger

engine = make_engine()
init_database(engine)
with sessionmaker(engine)() as db:
    result = verify_ledger(db)
print(json.dumps(result, indent=2))
if not result["ok"]:
    raise SystemExit(1)
