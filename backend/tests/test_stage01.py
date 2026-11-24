import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, func, text
from sqlalchemy.exc import IntegrityError

from app import schema as s
from app.config import Settings
from app.database import create_database, immediate_transaction
from app.main import create_app
from app.seed import STAMP, seed_demo, uid


@pytest.fixture
def migrated(tmp_path, monkeypatch):
    runtime = tmp_path / 'isolated'
    monkeypatch.setenv('RUNTIME_DIR', str(runtime))
    command.upgrade(Config('alembic.ini'), 'head')
    engine = create_database(runtime)
    yield engine, runtime
    engine.dispose()


def count(conn, table):
    return conn.execute(select(func.count()).select_from(table)).scalar_one()


def test_migration_seed_idempotence_and_restart(migrated):
    engine, runtime = migrated
    seed_demo(engine)
    with engine.connect() as conn:
        before = {t.name: count(conn, t) for t in s.metadata.sorted_tables}
        assert conn.execute(text('PRAGMA foreign_key_check')).all() == []
        assert before['departments'] == 6 and before['issues'] == 8
        assert before['resolution_rounds'] == 1 and before['confidential_cases'] == 1
        assert conn.execute(select(s.users.c.demo)).scalars().all() == [True] * before['users']
    seed_demo(engine)
    engine.dispose()
    reopened = create_database(runtime)
    try:
        with reopened.connect() as conn:
            assert before == {t.name: count(conn, t) for t in s.metadata.sorted_tables}
            assert conn.execute(select(s.issues.c.safe_title)).scalars().first()
    finally: reopened.dispose()


@pytest.mark.parametrize('table,values', [
    (s.verified_identities, lambda: dict(token='test-token',user_id=uid('user:student1'),created_at=STAMP)),
    (s.community_votes, lambda: dict(id=uid('vote:1'),issue_id=uid('issue:low'),user_id=uid('user:student2'),choice='2ND',created_at=STAMP,updated_at=STAMP)),
    (s.issue_participants, lambda: dict(id=uid('part:1'),issue_id=uid('issue:low'),user_id=uid('user:student2'),source='SECOND',first_joined=STAMP)),
    (s.trust_events, lambda: dict(id=uid('trust:1'),user_id=uid('user:student2'),event_key='event:1',delta=5,reason='synthetic',source_ref='evidence',created_at=STAMP)),
])
def test_essential_uniqueness(migrated, table, values):
    engine,_ = migrated
    seed_demo(engine)
    first = values()
    with engine.begin() as conn: conn.execute(insert(table).values(**first))
    duplicate = dict(first)
    if 'id' in duplicate: duplicate['id'] = uid('different:'+table.name)
    if table is s.verified_identities: duplicate['token'] = 'another-token'
    with pytest.raises(IntegrityError):
        with engine.begin() as conn: conn.execute(insert(table).values(**duplicate))


def test_identity_token_and_foreign_key_constraints(migrated):
    engine,_=migrated;seed_demo(engine)
    with engine.begin() as conn:
        conn.execute(insert(s.verified_identities).values(token='hash',user_id=uid('user:student1'),created_at=STAMP))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn: conn.execute(insert(s.verified_identities).values(token='hash',user_id=uid('user:student2'),created_at=STAMP))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn: conn.execute(insert(s.issue_participants).values(id=uid('bad'),issue_id=uid('absent'),user_id=uid('user:student1'),source='REPORTER',first_joined=STAMP))


def test_active_fingerprint_open_round_and_vote_eligibility(migrated):
    engine,_=migrated;seed_demo(engine)
    with engine.connect() as conn:
        original = dict(conn.execute(select(s.issues).where(s.issues.c.id==uid('issue:low'))).mappings().one())
    original['id']=uid('issue:duplicate')
    with pytest.raises(IntegrityError):
        with engine.begin() as conn: conn.execute(insert(s.issues).values(**original))
    original['status']='VERIFIED_CLOSED'
    with engine.begin() as conn: conn.execute(insert(s.issues).values(**original))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn: conn.execute(insert(s.resolution_rounds).values(id=uid('round:two'),issue_id=uid('issue:high'),sequence=2,opened_at=STAMP,deadline=STAMP,state='OPEN'))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn: conn.execute(insert(s.resolution_votes).values(id=uid('vote:ineligible'),round_id=uid('round:high'),user_id=uid('user:student3'),choice='CONFIRM',created_at=STAMP,updated_at=STAMP))


def test_resolution_vote_uniqueness_and_immutable_ledger(migrated):
    engine,_=migrated;seed_demo(engine)
    with engine.begin() as conn:
        conn.execute(insert(s.resolution_votes).values(id=uid('rv:1'),round_id=uid('round:high'),user_id=uid('user:student1'),choice='CONFIRM',created_at=STAMP,updated_at=STAMP))
        conn.execute(insert(s.trust_events).values(id=uid('te:1'),user_id=uid('user:student1'),event_key='immutable',delta=5,reason='fixture',source_ref='test',created_at=STAMP))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn: conn.execute(insert(s.resolution_votes).values(id=uid('rv:2'),round_id=uid('round:high'),user_id=uid('user:student1'),choice='DISPUTE',created_at=STAMP,updated_at=STAMP))
    for query in ["UPDATE trust_events SET delta=99", "DELETE FROM trust_events"]:
        with pytest.raises(IntegrityError):
            with engine.begin() as conn: conn.execute(text(query))


def test_write_transaction_rolls_back(migrated):
    engine,_=migrated
    with pytest.raises(RuntimeError):
        with immediate_transaction(engine) as conn:
            conn.execute(insert(s.departments).values(code='T',label='Test'))
            raise RuntimeError('rollback')
    with engine.connect() as conn: assert count(conn,s.departments)==0


def test_registry_endpoints(migrated):
    engine,runtime=migrated;seed_demo(engine)
    with TestClient(create_app(Settings(runtime_dir=runtime))) as client:
        deps=client.get('/api/v1/departments');locations=client.get('/api/v1/locations');categories=client.get('/api/v1/categories')
        assert deps.status_code==locations.status_code==categories.status_code==200
        assert {x['code'] for x in deps.json()} == {'EE','CSE','IS','LIBRARY','CAFETERIA','LABS'}
        assert all(x['demo'] for x in locations.json())
        assert any(x['name']=='Lab 3' for x in locations.json())
        assert any(x['code']=='OTHER' and x['parent_id'] is None for x in categories.json())
        assert all(set(x)=={'id','parent_id','code','label'} for x in categories.json())
