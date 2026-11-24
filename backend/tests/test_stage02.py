from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app import identity, schema as s
from app.config import Settings
from app.database import create_database
from app.main import create_app
from app.seed import seed_demo

ORIGIN={'origin':'http://127.0.0.1:8000'}

@pytest.fixture
def prepared(tmp_path, monkeypatch):
    def build(name, demo):
        path=tmp_path/name
        monkeypatch.setenv('RUNTIME_DIR',str(path))
        command.upgrade(Config('alembic.ini'),'head')
        engine=create_database(path)
        if demo: seed_demo(engine)
        engine.dispose()
        settings=Settings(runtime_dir=path,demo_mode=demo,allowed_student_email_domains='example.edu',smtp_host='mail.example',smtp_from='noreply@example.edu')
        return TestClient(create_app(settings),client=('127.0.0.1',50000)),path
    return build

def bootstrap(client,path):
    capability=(path/'demo-operator.token').read_text().strip()
    return client.post('/api/v1/demo/bootstrap',headers={**ORIGIN,'x-demo-operator-token':capability})

def test_demo_controls_sessions_and_reset(prepared):
    client,path=prepared('demo',True)
    with client:
        assert client.get('/api/v1/demo/users').status_code==401
        assert bootstrap(client,path).status_code==200
        students=client.get('/api/v1/demo/users').json()
        assert all(x['synthetic'] for x in students)
        old=client.cookies.get(identity.COOKIE)
        created=client.post('/api/v1/demo/create-student',headers=ORIGIN).json()
        assert client.post('/api/v1/demo/switch-user',headers=ORIGIN,json={'user':created['selector']}).status_code==200
        assert client.get('/api/v1/auth/me').json()['synthetic'] is True
        stale=TestClient(client.app,client=('127.0.0.1',50001),cookies={identity.COOKIE:old})
        assert stale.get('/api/v1/auth/me').status_code==401
        assert client.post('/api/v1/demo/advance-time',headers=ORIGIN,json={'hours':3}).status_code==200
        assert client.post('/api/v1/demo/provider-mode',headers=ORIGIN,json={'unavailable':True}).json()['unavailable'] is True
        (path/'uploads').mkdir()
        (path/'uploads'/'synthetic.txt').write_text('synthetic')
        old=client.cookies.get(identity.COOKIE)
        assert client.post('/api/v1/demo/reset',headers=ORIGIN).json()['reset'] is True
        assert not (path/'uploads').exists()
        assert client.get('/api/v1/demo/users').status_code==200
        stale.cookies.set(identity.COOKIE,old)
        assert stale.get('/api/v1/auth/me').status_code==401
        assert created['selector'] not in [x['selector'] for x in client.get('/api/v1/demo/users').json()]
        assert client.post('/api/v1/auth/logout',headers=ORIGIN).status_code==200
        assert client.get('/api/v1/auth/me').status_code==401

def test_demo_controls_origin_and_mode(prepared):
    client,path=prepared('demo',True)
    with client:
        capability=(path/'demo-operator.token').read_text().strip()
        assert client.post('/api/v1/demo/bootstrap',headers={'origin':'http://evil.test','x-demo-operator-token':capability}).status_code==403
        assert client.post('/api/v1/demo/bootstrap',headers=ORIGIN).status_code==403
        assert client.post('/api/v1/auth/request-otp',headers=ORIGIN,json={'email':'x@example.edu'}).status_code==403
    real,_=prepared('real',False)
    with real:
        assert real.post('/api/v1/demo/bootstrap',headers=ORIGIN).status_code==404

def test_otp_verification_reuse_uniqueness_and_privacy(prepared,monkeypatch):
    sent=[]
    monkeypatch.setattr(identity,'send_otp',lambda settings,recipient,code: sent.append(code))
    client,_=prepared('real',False)
    with client:
        first=client.post('/api/v1/auth/request-otp',headers=ORIGIN,json={'email':' Student@Example.edu '})
        challenge=first.json()['challenge'];code=sent[-1]
        assert client.post('/api/v1/auth/verify-otp',headers=ORIGIN,json={'challenge':challenge,'code':'000000' if code!='000000' else '999999'}).status_code==400
        assert client.post('/api/v1/auth/verify-otp',headers=ORIGIN,json={'challenge':challenge,'code':code}).status_code==200
        assert client.post('/api/v1/auth/verify-otp',headers=ORIGIN,json={'challenge':challenge,'code':code}).status_code==400
        info=client.get('/api/v1/auth/me').json()
        assert info['verified'] and not info['synthetic']
        assert not ({'id','email','token','user_id'} & info.keys())
        second=client.post('/api/v1/auth/request-otp',headers=ORIGIN,json={'email':'student@example.edu'}).json()['challenge']
        assert client.post('/api/v1/auth/verify-otp',headers=ORIGIN,json={'challenge':second,'code':sent[-1]}).status_code==200
        with client.app.state.engine.connect() as conn:
            assert len(conn.execute(select(s.verified_identities)).all())==1
            assert len(conn.execute(select(s.users)).all())==1
            assert not conn.execute(select(s.verification_challenges)).all()
            assert 'student@example.edu' not in str(conn.execute(select(s.verified_identities)).all()).lower()

def test_otp_expiry_attempts_and_concurrency(prepared,monkeypatch):
    sent=[];monkeypatch.setattr(identity,'send_otp',lambda settings,recipient,code: sent.append(code))
    client,_=prepared('real',False)
    with client:
        c=client.post('/api/v1/auth/request-otp',headers=ORIGIN,json={'email':'one@example.edu'}).json()['challenge']
        with client.app.state.engine.begin() as conn:
            conn.execute(update(s.verification_challenges).where(s.verification_challenges.c.id==c).values(expires_at=identity.stamp(identity.now()-timedelta(seconds=1))))
        assert client.post('/api/v1/auth/verify-otp',headers=ORIGIN,json={'challenge':c,'code':sent[-1]}).status_code==400
        c=client.post('/api/v1/auth/request-otp',headers=ORIGIN,json={'email':'two@example.edu'}).json()['challenge'];code=sent[-1]
        wrong='000000' if code!='000000' else '999999'
        for _ in range(5): assert client.post('/api/v1/auth/verify-otp',headers=ORIGIN,json={'challenge':c,'code':wrong}).status_code==400
        assert client.post('/api/v1/auth/verify-otp',headers=ORIGIN,json={'challenge':c,'code':code}).status_code==400
        c=client.post('/api/v1/auth/request-otp',headers=ORIGIN,json={'email':'three@example.edu'}).json()['challenge'];code=sent[-1]
        def verify(_): return client.post('/api/v1/auth/verify-otp',headers=ORIGIN,json={'challenge':c,'code':code}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool: assert sorted(pool.map(verify,range(2)))==[200,400]

def test_role_authorization():
    staff={'role':'STAFF','department_id':'CSE','confidential_capability':False}
    identity.require_department(staff,'CSE')
    with pytest.raises(HTTPException): identity.require_department(staff,'EE')
    with pytest.raises(HTTPException): identity.require_confidential(staff)
    identity.require_confidential({'confidential_capability':True})
