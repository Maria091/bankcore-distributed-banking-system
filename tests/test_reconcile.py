from bankcore.models import Account
from bankcore.reconcile import verify_ledger

def test_reconciler_passes_good_ledger(environment, client, headers, funded):
    a,b=funded
    result=client.post('/v1/transfers',json={'source_account_id':a,'destination_account_id':b,'amount_minor':3000},
                       headers={**headers,'Idempotency-Key':'reconcile-move-01'})
    assert result.status_code == 201
    _, _, app = environment
    with app.state.SessionLocal() as db:
        report = verify_ledger(db)
        assert report['ok'] and report['checked_transfers'] == 2

def test_reconciler_detects_corrupted_projection(environment,client,headers,funded):
    a,b=funded
    _,_,app=environment
    with app.state.SessionLocal.begin() as db:
        record=db.get(Account,a)
        record.balance_minor+=1
    with app.state.SessionLocal() as db:
        report=verify_ledger(db)
        assert not report['ok']
        assert any('Balance projection mismatch' in e for e in report['errors'])
