from concurrent.futures import ThreadPoolExecutor

def test_same_key_concurrent_replays_one_transfer(environment, client, headers, funded):
    source, destination = funded
    payload = {'source_account_id': source, 'destination_account_id': destination,
               'amount_minor': 1000, 'reference': 'same-logical-request'}
    h = {**headers, 'Idempotency-Key': 'concurrent-same-key-0001'}
    def send(_):
        result = client.post('/v1/transfers', json=payload, headers=h)
        return result.status_code, result.json()
    with ThreadPoolExecutor(max_workers=6) as pool:
        replies = list(pool.map(send, range(10)))
    assert all(code == 201 for code, _ in replies), replies
    assert len({reply['id'] for _, reply in replies}) == 1
    assert client.get(f'/v1/accounts/{source}', headers=headers).json()['balance_minor'] == 49000
    assert client.get(f'/v1/accounts/{destination}', headers=headers).json()['balance_minor'] == 1000
