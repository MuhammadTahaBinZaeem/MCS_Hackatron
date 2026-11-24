from fastapi.testclient import TestClient
from test_stage02 import prepared,bootstrap,ORIGIN
from test_stage03 import student_client
from app.seed import uid

def test_publish_group_priority_and_privacy(prepared):
    client,path=prepared('demo',True)
    with client:
        student_client(client,path)
        data={'text':'wifi not working on PC 5 in lab 4','category_id':uid('cat:NETWORK:WIFI')}
        first=client.post('/api/v1/reports',headers={**ORIGIN,'Idempotency-Key':'first'},json=data).json()
        assert first['issue_id']
        second=client.post('/api/v1/reports',headers={**ORIGIN,'Idempotency-Key':'second'},json=data).json()
        assert second['issue_id']==first['issue_id']
        issue=client.get('/api/v1/issues/'+first['issue_id']).json()
        assert issue['affected_count']==1 and issue['priority']['score']<=89
        changed=client.post('/api/v1/reports',headers={**ORIGIN,'Idempotency-Key':'other'},json={**data,'text':'wifi not working on PC 8 in lab 4'}).json()
        assert changed['issue_id']!=first['issue_id']
        other=client.post('/api/v1/reports',headers={**ORIGIN,'Idempotency-Key':'ac'},json={'text':'ac not working lab 4'}).json()
        assert other['issue_id'] and other['issue_id']!=first['issue_id']
        private=client.post('/api/v1/reports',headers={**ORIGIN,'Idempotency-Key':'private'},json={'text':'ragging in lab 4'}).json()
        assert private['issue_id'] is None
        hazard=client.post('/api/v1/reports',headers={**ORIGIN,'Idempotency-Key':'hazard'},json={'text':'sparks in lab 4'}).json()
        assert client.get('/api/v1/issues/'+hazard['issue_id']).json()['priority']['score']==100
