from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from bankcore.database import DEMO_TREASURY_CENTS
from bankcore.models import Account, LedgerEntry, Transfer, OutboxEvent, Notification
from bankcore.messaging import dispatch_pending, consume_notifications, counts

def test_double_entry_and_conservation(environment, client, headers, funded):
    a,b=funded
    for idx in range(5):
        r=client.post('/v1/transfers',json={'source_account_id':a,'destination_account_id':b,'amount_minor':1500},
                      headers={**headers,'Idempotency-Key':f'move-verify-{idx:05d}'})
        assert r.status_code==201
    _,_,app=environment
    with app.state.SessionLocal() as db:
        all_transfers=db.scalars(select(Transfer)).all()
        for transaction in all_transfers:
            entries=db.scalars(select(LedgerEntry).where(LedgerEntry.transfer_id==transaction.id)).all()
            if transaction.status=='POSTED':
                assert len(entries)==2
                assert sum(e.amount_minor for e in entries)==0
                assert {e.amount_minor for e in entries}=={-transaction.amount_minor,transaction.amount_minor}
            else:
                assert not entries
        total=db.scalar(select(func.sum(Account.balance_minor)))
        assert total==DEMO_TREASURY_CENTS
        assert db.scalar(select(func.count()).select_from(OutboxEvent))==len(all_transfers)

def test_failed_transfer_produces_no_posted_side_effect(environment, client, headers, funded):
    a,b=funded
    before=client.get('/v1/ops/stats',headers=headers).json()
    r=client.post('/v1/transfers',json={'source_account_id':a,'destination_account_id':b,'amount_minor':60000},
                  headers={**headers,'Idempotency-Key':'fail-00000001'})
    assert r.status_code==409
    assert client.get('/v1/ops/stats',headers=headers).json()==before

def test_outbox_dispatch_and_consumer_are_idempotent(environment,client,headers,funded):
    a,b=funded
    r=client.post('/v1/transfers',json={'source_account_id':a,'destination_account_id':b,'amount_minor':2500},
                  headers={**headers,'Idempotency-Key':'move-00001001'})
    assert r.status_code==201
    _,url,app=environment
    with app.state.SessionLocal.begin() as db:
        assert dispatch_pending(db)==2
        assert dispatch_pending(db)==0
        assert consume_notifications(db)==2
        assert consume_notifications(db)==0
        assert counts(db)=={'pending_outbox':0,'published_outbox':2,'broker_messages':2,'notifications':2}
    with app.state.SessionLocal.begin() as db:
        assert consume_notifications(db)==0
        assert db.scalar(select(func.count()).select_from(Notification))==2

def test_concurrent_spend_cannot_overdraft(environment,client,headers,account):
    a,b=account('Source'),account('Destination')
    r=client.post('/v1/demo/fund',json={'account_id':a,'amount_minor':20000},
                  headers={**headers,'Idempotency-Key':'fund-00001999'})
    assert r.status_code==201
    def send(idx):
        return client.post('/v1/transfers',json={'source_account_id':a,'destination_account_id':b,'amount_minor':5000},
                           headers={**headers,'Idempotency-Key':f'concurrent-{idx:08d}'}).status_code
    with ThreadPoolExecutor(max_workers=8) as ex:
        outcomes=list(ex.map(send,range(12)))
    assert outcomes.count(201)==4, outcomes
    assert outcomes.count(409)==8, outcomes
    assert client.get(f'/v1/accounts/{a}',headers=headers).json()['balance_minor']==0
    assert client.get(f'/v1/accounts/{b}',headers=headers).json()['balance_minor']==20000

# Local mock broker does not prove Kafka integration or distributed exactly-once delivery.
