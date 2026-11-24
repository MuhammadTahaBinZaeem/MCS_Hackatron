from test_stage02 import prepared,bootstrap,ORIGIN
from test_stage03 import student_client
from app.seed import uid

def test_self_vote_staff_scope_and_solo_review(prepared):
    client,path=prepared('demo',True)
    with client:
        student_client(client,path)
        users=client.get('/api/v1/demo/users').json()
        reporter=next(x for x in users if x['selector']==uid('user:student1'))
        client.post('/api/v1/demo/switch-user',headers=ORIGIN,json={'user':reporter['selector']})
        assert client.post('/api/v1/issues/'+uid('issue:low')+'/vote',headers=ORIGIN,json={'choice':'2ND'}).status_code==403
        staff=next(x for x in users if x['role']=='STAFF' and x['department']=='LABS')
        client.post('/api/v1/demo/switch-user',headers=ORIGIN,json={'user':staff['selector']})
        result=client.patch('/api/v1/staff/issues/'+uid('issue:low'),headers=ORIGIN,json={'status':'PENDING_VERIFICATION','version':1})
        assert result.status_code==200
        from sqlalchemy import select
        from app import schema as s
        with client.app.state.engine.connect() as conn:
            rid=conn.execute(select(s.resolution_rounds.c.id).where(s.resolution_rounds.c.issue_id==uid('issue:low'))).scalar_one()
        client.post('/api/v1/demo/switch-user',headers=ORIGIN,json={'user':reporter['selector']})
        result=client.post('/api/v1/issues/'+uid('issue:low')+'/resolution-vote',headers=ORIGIN,json={'round_id':rid,'choice':'DISPUTE'})
        assert result.status_code==200 and result.json()['outcome']=='REVIEW_REQUIRED'

def test_expiry_and_idempotent_trust_adjudication(prepared):
    client,path=prepared('demo',True)
    with client:
        bootstrap(client,path)
        result=client.post('/api/v1/demo/advance-time',headers=ORIGIN,json={'hours':49})
        assert result.status_code==200
        assert client.get('/api/v1/issues/'+uid('issue:high')).json()['status']=='REVIEW_REQUIRED'
        payload={'report_ref':uid('report:low'),'outcome':'VERIFIED_REPORT','evidence_ref':'synthetic-evidence'}
        assert client.post('/api/v1/admin/adjudicate',headers=ORIGIN,json=payload).status_code==200
        assert client.post('/api/v1/admin/adjudicate',headers=ORIGIN,json=payload).status_code==200
        client.post('/api/v1/demo/switch-user',headers=ORIGIN,json={'user':uid('user:student1')})
        trust=client.get('/api/v1/me/trust').json()
        assert trust['score']==55 and len(trust['events'])==1
