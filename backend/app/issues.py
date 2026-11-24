"""Canonical ordinary issues and deterministic priority."""
import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, Request
from sqlalchemy import insert, select, func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app import schema as s
from app.identity import err, get_session, require_department

router=APIRouter(prefix='/api/v1')
ACTIVE={'REPORTED','ACKNOWLEDGED','IN_PROGRESS','PENDING_VERIFICATION','REOPENED','REVIEW_REQUIRED'}

def timestamp(conn, demo):
    if demo:
        value=conn.execute(select(s.system_settings.c.value).where(s.system_settings.c.key=='demo_clock')).scalar()
        if value:return datetime.fromisoformat(value.replace('Z','+00:00'))
    return datetime.now(timezone.utc)

def priority(conn, issue, clock):
    if issue['hazard'] in {'SAFETY','MEDICAL'}:return {'score':100,'base':100,'crowd':0,'aging':0,'reason':'Safety hazard'}
    base={'MINOR':10,'PARTIAL_DISRUPTION':25,'COMPLETE_DISRUPTION':40,'MAJOR_DISRUPTION':60}[issue['impact']]
    rows=conn.execute(select(s.users.c.trust_cache).join(s.issue_participants,s.issue_participants.c.user_id==s.users.c.id).where(s.issue_participants.c.issue_id==issue['id'],s.issue_participants.c.valid.is_(True))).scalars()
    crowd=min(25,10*math.log1p(sum(0.5+x/100 for x in rows)))
    age=issue['active_unresolved_seconds']
    if issue['active_since'] and issue['status'] not in {'PENDING_VERIFICATION','VERIFIED_CLOSED'}:
        age+=max(0,(clock-datetime.fromisoformat(issue['active_since'].replace('Z','+00:00'))).total_seconds())
    aging=min(15,0.5*age/3600)
    score=min(89,int(Decimal(str(base+crowd+aging)).quantize(Decimal('1'),rounding=ROUND_HALF_UP)))
    return {'score':score,'base':base,'crowd':round(crowd,2),'aging':round(aging,2),'reason':'Impact, affected students and unresolved time'}

def candidate_issues(conn, proposal):
    root=conn.execute(select(s.categories.c.id).where(s.categories.c.parent_id.is_(None),s.categories.c.code==proposal['category'])).scalar()
    if not root:return [],None
    rows=conn.execute(select(s.issues).where(s.issues.c.location_id==proposal['location_id'],s.issues.c.category_id==root,s.issues.c.status.in_(ACTIVE))).mappings()
    compatible=[dict(row) for row in rows if (not row['subtype'] or not proposal['subcategory'] or row['subtype']==proposal['subcategory']) and (not row['failure'] or not proposal['failure_type'] or row['failure']==proposal['failure_type']) and (not row['asset'] or not proposal['asset_identifier'] or row['asset']==proposal['asset_identifier'])]
    return compatible,root

def semantic_suggestion(request, proposal, report_text):
    if proposal['visibility']!='PUBLIC' or proposal['clarification_required'] or not proposal['privacy_screen']['external_safe'] or proposal['processing_mode']!='RULES':return None
    with request.app.state.engine.connect() as conn:
        if conn.execute(select(s.system_settings.c.value).where(s.system_settings.c.key=='provider_unavailable')).scalar()=='true':return None
        candidates,_=candidate_issues(conn,proposal)
    if not candidates:return None
    if proposal['subcategory'] and proposal['failure_type'] and proposal['asset_identifier'] and any(row['subtype']==proposal['subcategory'] and row['failure']==proposal['failure_type'] and row['asset']==proposal['asset_identifier'] for row in candidates):return None
    try:
        result,status=request.app.state.text_provider.compare(report_text,[{'id':row['id'],'text':row['safe_description']} for row in candidates])
        return result.candidate_id if status=='AI' and result and result.decision=='SAME' and any(row['id']==result.candidate_id for row in candidates) else None
    except (ValueError,TypeError,KeyError,AttributeError):return None

def publish(conn, report_id, owner_id, proposal, clock, merge_id=None, separate=False):
    if proposal['visibility']!='PUBLIC' or proposal['clarification_required'] or not proposal['department']:
        return None,[]
    candidates,root=candidate_issues(conn,proposal)
    exact=bool(proposal['subcategory'] and proposal['failure_type'] and proposal['asset_identifier'])
    fingerprint=hashlib.sha256(json.dumps([proposal['location_id'],root,proposal['subcategory'],proposal['failure_type'],proposal['asset_identifier']],separators=(',',':')).encode()).hexdigest() if exact else None
    matching=next((r for r in candidates if fingerprint and r['fingerprint']==fingerprint),None)
    if merge_id:
        matching=next((r for r in candidates if r['id']==merge_id),None)
        if not matching:err(409,'Selected issue is no longer compatible')
    if matching and separate:err(409,'A specific matching issue already exists')
    if candidates and not matching and not separate:
        return None,[{'id':r['id'],'title':r['safe_title']} for r in candidates]
    issue_id=matching['id'] if matching else str(uuid.uuid4())
    if not matching:
        if not root:err(400,'Invalid category')
        closed=conn.execute(select(s.issues.c.id).where(s.issues.c.location_id==proposal['location_id'],s.issues.c.category_id==root,s.issues.c.status=='VERIFIED_CLOSED',s.issues.c.subtype==proposal['subcategory'],s.issues.c.failure==proposal['failure_type'],s.issues.c.asset==proposal['asset_identifier']).order_by(s.issues.c.created_at.desc())).scalar()
        ts=clock.isoformat()
        conn.execute(insert(s.issues).values(id=issue_id,department_id=proposal['department'],location_id=proposal['location_id'],category_id=root,subtype=proposal['subcategory'],failure=proposal['failure_type'],asset=proposal['asset_identifier'],safe_title=proposal['reason'],safe_description=proposal['reason'],impact=proposal['impact'],hazard='SAFETY' if proposal['priority_proposal']==100 else 'NONE',status='REPORTED',fingerprint=fingerprint,recurrence_of=closed,created_at=ts,updated_at=ts,active_since=ts))
    conn.execute(s.reports.update().where(s.reports.c.id==report_id).values(issue_id=issue_id))
    stmt=sqlite_insert(s.issue_participants).values(id=str(uuid.uuid4()),issue_id=issue_id,user_id=owner_id,source='REPORTER',first_joined=clock.isoformat(),valid=True)
    conn.execute(stmt.on_conflict_do_update(index_elements=['issue_id','user_id'],set_={'source':'REPORTER','valid':True}))
    conn.execute(s.community_votes.delete().where(s.community_votes.c.issue_id==issue_id,s.community_votes.c.user_id==owner_id))
    return issue_id,[]

def issue_dto(conn,row,clock,user_id=None):
    counts=conn.execute(select(func.count()).select_from(s.issue_participants).where(s.issue_participants.c.issue_id==row['id'],s.issue_participants.c.valid.is_(True))).scalar_one()
    votes=conn.execute(select(s.community_votes.c.choice,func.count()).where(s.community_votes.c.issue_id==row['id'],s.community_votes.c.valid.is_(True)).group_by(s.community_votes.c.choice)).all()
    own=conn.execute(select(s.community_votes.c.choice).where(s.community_votes.c.issue_id==row['id'],s.community_votes.c.user_id==user_id,s.community_votes.c.valid.is_(True))).scalar() if user_id else None
    round_=conn.execute(select(s.resolution_rounds.c.id,s.resolution_rounds.c.deadline).where(s.resolution_rounds.c.issue_id==row['id'],s.resolution_rounds.c.state=='OPEN')).mappings().first()
    eligible=bool(round_ and user_id and conn.execute(select(s.voter_eligibility.c.user_id).where(s.voter_eligibility.c.round_id==round_['id'],s.voter_eligibility.c.user_id==user_id,s.voter_eligibility.c.valid.is_(True))).first())
    return {'id':row['id'],'title':row['safe_title'],'description':row['safe_description'],'department':row['department_id'],'location_id':row['location_id'],'category_id':row['category_id'],'status':row['status'],'priority':priority(conn,row,clock),'affected_count':counts,'vote_counts':dict(votes),'own_vote':own,'resolution':{'round_id':round_['id'],'deadline':round_['deadline'],'eligible':eligible} if round_ else None,'created_at':row['created_at'],'version':row['version']}

@router.get('/issues')
def list_issues(request:Request,department:str|None=None,q:str|None=None,category:str|None=None,status:str|None=None,priority_level:str|None=None,sort:str='priority',offset:int=0,limit:int=25,session=Depends(get_session)):
    if sort not in {'priority','newest','support'} or offset<0 or not 1<=limit<=100:err(400,'Invalid list parameters')
    from app.community import process_expiry
    process_expiry(request)
    with request.app.state.engine.connect() as conn:
        query=select(s.issues)
        if department:query=query.where(s.issues.c.department_id==department)
        if q:query=query.where(s.issues.c.safe_title.contains(q,autoescape=True))
        if category:query=query.where(s.issues.c.category_id==category)
        if status:query=query.where(s.issues.c.status==status)
        clock=timestamp(conn,request.app.state.config.demo_mode)
        results=[issue_dto(conn,dict(row),clock,session['user_id']) for row in conn.execute(query).mappings()]
    if priority_level:
        bounds={'LOW':(0,24),'MEDIUM':(25,49),'HIGH':(50,89),'CRITICAL':(90,100)}
        if priority_level not in bounds:err(400,'Invalid priority')
        low,high=bounds[priority_level];results=[row for row in results if low<=row['priority']['score']<=high]
    if sort=='priority':results.sort(key=lambda x:(-x['priority']['score'],x['created_at'],x['id']))
    elif sort=='support':results.sort(key=lambda x:(-x['affected_count'],x['created_at'],x['id']))
    else:results.sort(key=lambda x:(x['created_at'],x['id']),reverse=True)
    return results[offset:offset+limit]

@router.get('/issues/{issue_id}')
def get_issue(issue_id:str,request:Request,session=Depends(get_session)):
    from app.community import process_expiry
    process_expiry(request)
    with request.app.state.engine.connect() as conn:
        row=conn.execute(select(s.issues).where(s.issues.c.id==issue_id)).mappings().first()
        if not row:err(404,'Not found')
        return issue_dto(conn,dict(row),timestamp(conn,request.app.state.config.demo_mode),session['user_id'])

@router.get('/staff/queue')
def staff_queue(request:Request,session=Depends(get_session)):
    if session['role']!='STAFF':err(403,'Forbidden')
    return list_issues(request,department=session['department_id'],session=session)

@router.get('/admin/issues')
def admin_issues(request:Request,session=Depends(get_session)):
    if session['role']!='ADMIN':err(403,'Forbidden')
    return list_issues(request,session=session)
