"""Local outbox/consumer worker. Real broker integration belongs to a later phase."""
from sqlalchemy.orm import sessionmaker
from bankcore.database import make_engine, init_database
from bankcore.messaging import dispatch_pending, consume_notifications, counts

def run_once(url: str | None = None):
    engine = make_engine(url)
    init_database(engine)
    Session = sessionmaker(engine)
    with Session.begin() as db:
        sent = dispatch_pending(db)
        delivered = consume_notifications(db)
        result = {"dispatched": sent, "new_notifications": delivered, **counts(db)}
    engine.dispose()
    return result

if __name__ == "__main__":
    print(run_once())
