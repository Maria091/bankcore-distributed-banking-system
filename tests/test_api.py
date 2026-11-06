from uuid import uuid4

def test_health_and_auth(client, headers):
    assert client.get('/health/live').json() == {'status': 'ok'}
    assert client.get('/v1/ops/stats').status_code == 401
    assert client.get('/health/ready', headers=headers).json()['status'] == 'ok'

def test_account_create_read_and_no_treasury_access(client, account, headers):
    aid = account('Alice')
    a = client.get(f'/v1/accounts/{aid}', headers=headers).json()
    assert a['currency'] == 'USD' and a['balance_minor'] == 0
    assert client.get('/v1/accounts/00000000-0000-0000-0000-000000000001', headers=headers).status_code == 404

def test_transfer_balances_and_ledger(client, headers, funded):
    a,b = funded
    body = {'source_account_id':a, 'destination_account_id':b, 'amount_minor':12500, 'reference':'Demo transfer'}
    result = client.post('/v1/transfers', json=body, headers={**headers,'Idempotency-Key':'move-00000001'})
    assert result.status_code == 201, result.text
    assert result.json()['status'] == 'POSTED'
    assert client.get(f'/v1/accounts/{a}', headers=headers).json()['balance_minor'] == 37500
    assert client.get(f'/v1/accounts/{b}', headers=headers).json()['balance_minor'] == 12500
    entries = client.get(f'/v1/accounts/{b}/ledger', headers=headers).json()
    assert len(entries) == 1 and entries[0]['amount_minor'] == 12500
    assert client.get(f"/v1/transfers/{result.json()['id']}",headers=headers).json()['kind'] == 'TRANSFER'

def test_key_same_request_same_effect(client, headers, funded):
    a,b = funded
    body = {'source_account_id':a, 'destination_account_id':b, 'amount_minor':2500}
    h={**headers, 'Idempotency-Key':'move-00000002'}
    one=client.post('/v1/transfers',json=body,headers=h)
    two=client.post('/v1/transfers',json=body,headers=h)
    assert one.status_code == two.status_code == 201
    assert one.json()==two.json()
    assert client.get(f'/v1/accounts/{b}',headers=headers).json()['balance_minor'] == 2500

def test_key_changed_payload_is_conflict(client, headers, funded):
    a,b=funded
    h={**headers,'Idempotency-Key':'move-00000003'}
    body={'source_account_id':a,'destination_account_id':b,'amount_minor':1000}
    assert client.post('/v1/transfers',json=body,headers=h).status_code==201
    assert client.post('/v1/transfers',json={**body, 'amount_minor':2000},headers=h).status_code==409

def test_key_reuse_across_endpoints_conflict(client, headers, funded):
    a,b=funded
    h={**headers,'Idempotency-Key':'move-00000004'}
    result=client.post('/v1/transfers',json={'source_account_id':a,'destination_account_id':b,'amount_minor':1000},headers=h)
    assert result.status_code==201
    result=client.post('/v1/demo/fund',json={'account_id':a,'amount_minor':1000},headers=h)
    assert result.status_code==409

def test_cannot_overdraw_or_transfer_to_self(client, headers, funded):
    a,b=funded
    head={**headers,'Idempotency-Key':'move-00000005'}
    for body,expected in [({'source_account_id':a,'destination_account_id':b,'amount_minor':60000},409),
                          ({'source_account_id':a,'destination_account_id':a,'amount_minor':100},422)]:
        r=client.post('/v1/transfers',json=body,headers=head)
        assert r.status_code==expected
    assert client.get(f'/v1/accounts/{a}',headers=headers).json()['balance_minor']==50000
    assert client.get(f'/v1/accounts/{b}',headers=headers).json()['balance_minor']==0

def test_review_not_booked(client, headers, account):
    a,b=account('Alice'),account('Bob')
    client.post('/v1/demo/fund',json={'account_id':a,'amount_minor':2_000_000},
                headers={**headers,'Idempotency-Key':'fund-00000008'}).raise_for_status()
    r=client.post('/v1/transfers',json={'source_account_id':a,'destination_account_id':b,'amount_minor':1_000_000},
                  headers={**headers,'Idempotency-Key':'move-00000008'})
    assert r.status_code==201 and r.json()['status']=='REVIEW_REQUIRED'
    assert client.get(f'/v1/accounts/{a}',headers=headers).json()['balance_minor']==2_000_000
    assert client.get(f'/v1/accounts/{b}',headers=headers).json()['balance_minor']==0
    assert client.get(f'/v1/accounts/{b}/ledger',headers=headers).json()==[]

def test_strict_money_validation(client, headers, funded):
    a,b=funded
    for amount in (-1, 0, 3.2, '100', True, 20000000):
        r=client.post('/v1/transfers',json={'source_account_id':a,'destination_account_id':b,'amount_minor':amount},
                      headers={**headers,'Idempotency-Key':str(uuid4())})
        assert r.status_code==422, (amount,r.status_code,r.text)

def test_missing_or_invalid_idempotency_key(client, headers, funded):
    a,b=funded
    body={'source_account_id':a,'destination_account_id':b,'amount_minor':100}
    assert client.post('/v1/transfers',json=body,headers=headers).status_code==400
    assert client.post('/v1/transfers',json=body,headers={**headers,'Idempotency-Key':'a b c d e'}).status_code==400

def test_missing_and_invalid_accounts(client,headers,account):
    a=account('Alice')
    r=client.post('/v1/transfers',json={'source_account_id':a,'destination_account_id':str(uuid4()),'amount_minor':100},
                  headers={**headers,'Idempotency-Key':'move-00000009'})
    assert r.status_code==404
