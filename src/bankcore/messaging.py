"""Deterministic local outbox dispatcher and idempotent notification consumer.

No networked queue: this is deliberately an in-DB mock broker for free local development.
"""
import json
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from bankcore.models import OutboxEvent, BrokerMessage, Notification, utcnow

def dispatch_pending(db: Session, limit: int = 100) -> int:
    if not 1 <= limit <= 1000: raise ValueError("limit must be between 1 and 1000")
    events = db.scalars(select(OutboxEvent).where(OutboxEvent.state == "PENDING")
                        .order_by(OutboxEvent.created_at, OutboxEvent.id).limit(limit)).all()
    for event in events:
        if db.get(BrokerMessage, event.id) is None:
            db.add(BrokerMessage(event_id=event.id, event_type=event.event_type,
                                 payload_json=event.payload_json))
        event.state = "PUBLISHED"
        event.published_at = utcnow()
    db.flush()
    return len(events)

def consume_notifications(db: Session, limit: int = 100) -> int:
    if not 1 <= limit <= 1000: raise ValueError("limit must be between 1 and 1000")
    messages = db.scalars(select(BrokerMessage).order_by(BrokerMessage.created_at, BrokerMessage.event_id)).all()
    created = 0
    for event in messages:
        if created >= limit: break
        if db.get(Notification, event.event_id): continue
        transfer = json.loads(event.payload_json)
        msg = (f"Synthetic transfer {transfer['id']} requires review" if event.event_type == "transfer.review_requested"
               else f"Synthetic transfer {transfer['id']} posted")
        db.add(Notification(event_id=event.event_id, message=msg))
        created += 1
    db.flush()
    return created

def counts(db: Session):
    return {"pending_outbox": db.scalar(select(func.count()).select_from(OutboxEvent)
                                        .where(OutboxEvent.state == "PENDING")),
            "published_outbox": db.scalar(select(func.count()).select_from(OutboxEvent)
                                          .where(OutboxEvent.state == "PUBLISHED")),
            "broker_messages": db.scalar(select(func.count()).select_from(BrokerMessage)),
            "notifications": db.scalar(select(func.count()).select_from(Notification))}
