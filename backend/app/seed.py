"""Idempotent synthetic demo fixtures; no real identities or campus claims."""
import argparse
from contextlib import nullcontext
from uuid import uuid5, NAMESPACE_URL

from sqlalchemy.dialects.sqlite import insert
from app.config import Settings
from app.database import create_database, immediate_transaction
from app import schema as s

STAMP = '2026-01-01T12:00:00Z'

def uid(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, 'reportfix-demo:' + name))

def seed_demo(engine, connection=None):
    with (immediate_transaction(engine) if connection is None else nullcontext(connection)) as conn:
        def add(table, **values):
            conn.execute(insert(table).values(**values).on_conflict_do_nothing())
        for code, label in [('EE','EE'),('CSE','CSE'),('IS','IS'),('LIBRARY','Library'),('CAFETERIA','Cafeteria'),('LABS','Labs')]:
            add(s.departments,code=code,label=label)
            add(s.locations,id=uid('loc:'+code),name=label,canonical_path=code,department_id=code,demo=True,active=True)
        for key,name,parent,dept,alias in [('lab3','Lab 3','LABS','LABS','lab 3'),('lab4','Lab 4','LABS','LABS','lab 4'),('cse_lab3','CSE Lab 3','CSE','CSE','lab 3'),('library_reading','Library Reading Area','LIBRARY','LIBRARY','reading area')]:
            location=uid('loc:'+key)
            add(s.locations,id=location,parent_id=uid('loc:'+parent),department_id=dept,name=name,canonical_path=parent+'/'+key,demo=True,active=True)
            add(s.location_aliases,id=uid('alias:'+key),location_id=location,normalized_alias=alias)
        taxonomy = {
            'NETWORK': ('IT / Network',['WIFI','INTERNET','LAN']), 'COMPUTING': ('Computing',['HARDWARE','SOFTWARE']),
            'ELECTRICAL': ('Electrical',['POWER','LIGHTS','SOCKETS','FANS']), 'FACILITIES': ('Facilities',['HVAC','PLUMBING','SANITATION','FURNITURE','INFRASTRUCTURE']),
            'ACADEMIC': ('Academic',['PROJECTOR','WHITEBOARD','LAB_EQUIPMENT','SERVICES']), 'CAFETERIA': ('Cafeteria',['FOOD','HYGIENE','WATER']),
            'SAFETY': ('Safety',['FIRE','GAS','SPARKS','STRUCTURAL_HAZARD']), 'MEDICAL': ('Medical',['EMERGENCY']), 'CONDUCT': ('Conduct',['HARASSMENT','RAGGING'])}
        add(s.categories,id=uid('cat:OTHER'),code='OTHER',label='Other',active=True)
        for code,(label,children) in taxonomy.items():
            root=uid('cat:'+code)
            add(s.categories,id=root,code=code,label=label,active=True)
            for child in [*children,'OTHER']:
                child_id=uid('cat:'+code+':'+child)
                add(s.categories,id=child_id,parent_id=root,code=child,label=child.replace('_',' ').title(),active=True)
                if child != 'OTHER':
                    add(s.categories,id=uid('cat:'+code+':'+child+':OTHER'),parent_id=child_id,code='OTHER',label='Other',active=True)
        people=[('student1','STUDENT',None,False),('student2','STUDENT',None,False),('student3','STUDENT',None,False),('admin','ADMIN',None,False),('handler','ADMIN',None,True)] + [('staff_'+code,'STAFF',code,False) for code in ['EE','CSE','IS','LIBRARY','CAFETERIA','LABS']]
        for name,role,dept,cap in people:
            add(s.users,id=uid('user:'+name),role=role,department_id=dept,confidential_capability=cap,verified=True,demo=True,created_at=STAMP,trust_cache=50)
        fixtures=[('low','Broken chair','FACILITIES','MINOR','NONE','REPORTED','lab3','2026-01-01T11:30:00Z'),('medium','Room light not working','ELECTRICAL','PARTIAL_DISRUPTION','NONE','ACKNOWLEDGED','lab4','2026-01-01T08:00:00Z'),('high','Network unavailable','NETWORK','COMPLETE_DISRUPTION','NONE','PENDING_VERIFICATION','cse_lab3','2025-12-31T08:00:00Z'),('critical','Exposed electrical sparks','SAFETY','MAJOR_DISRUPTION','SAFETY','REPORTED','lab3','2026-01-01T11:45:00Z')]
        for name,title,cat,impact,hazard,status,loc,created in fixtures:
            issue=uid('issue:'+name); dept='CSE' if loc=='cse_lab3' else 'LABS'
            add(s.issues,id=issue,department_id=dept,location_id=uid('loc:'+loc),category_id=uid('cat:'+cat),safe_title=title,safe_description='Synthetic demo: '+title.lower(),impact=impact,hazard=hazard,status=status,fingerprint='synthetic-'+name,created_at=created,updated_at=STAMP,active_since=created if status!='PENDING_VERIFICATION' else None)
            add(s.reports,id=uid('report:'+name),owner_id=uid('user:student1'),issue_id=issue,visibility='PUBLIC',safe_extracted_fields='{}',clarification_state='NONE',created_at=created,request_key='seed-'+name)
            add(s.issue_participants,id=uid('participant:'+name),issue_id=issue,user_id=uid('user:student1'),source='REPORTER',first_joined=created,valid=True)
        add(s.resolution_rounds,id=uid('round:high'),issue_id=uid('issue:high'),sequence=1,opened_at=STAMP,deadline='2026-01-03T12:00:00Z',state='OPEN')
        add(s.voter_eligibility,round_id=uid('round:high'),user_id=uid('user:student1'),frozen_weight=1.0,valid=True)
        add(s.confidential_cases,id=uid('case:example'),safe_content='Synthetic restricted case',status='OPEN',hazard='NONE',created_at=STAMP,updated_at=STAMP)
        add(s.confidential_ownership,case_id=uid('case:example'),user_id=uid('user:student2'))
        add(s.reports,id=uid('report:confidential'),owner_id=uid('user:student2'),case_id=uid('case:example'),visibility='CONFIDENTIAL',safe_extracted_fields='{}',clarification_state='NONE',created_at=STAMP,request_key='seed-confidential')
        add(s.system_settings,key='demo_clock',value=STAMP)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--demo',action='store_true',required=True);parser.parse_args()
    settings=Settings()
    if not settings.demo_mode: raise SystemExit('Demo seeding requires DEMO_MODE=true')
    engine=create_database(settings.runtime_dir)
    try: seed_demo(engine)
    finally: engine.dispose()
    print('Synthetic demo seed applied.')

if __name__ == '__main__': main()
