import uuid
from datetime import timedelta,datetime
from typing import Literal
from fastapi import APIRouter,Depends,Request
from pydantic import BaseModel
from sqlalchemy import select,insert,update,delete,func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app import schema as s
from app.database import immediate_transaction
from app.identity import err,get_session,require_department
from app.issues import timestamp

router=APIRouter(prefix='/api/v1')
class Vote(BaseModel): choice:Literal['2ND','DISAGREE']
class ResolveVote(BaseModel): round_id:str;choice:Literal['CONFIRM','DISPUTE']
class Transition(BaseModel): status:Literal['ACKNOWLEDGED','IN_PROGRESS','PENDING_VERIFICATION'];version:int;reason:str=''
class Adjudication(BaseModel):
    report_ref:str=''
    round_ref:str=''
    outcome:Literal['VERIFIED_REPORT','CONFIRMED_SPAM','DELIBERATE_FAKE','MALICIOUS_ABUSE','VERIFIED_FIX','VERIFIED_UNRESOLVED']
    evidence_ref:str

class Reversal(BaseModel):
    source_ref:str
    reason:Literal['VERIFIED_REPORT','VERIFIED_JOIN','CONFIRMED_SPAM','DELIBERATE_FAKE','MALICIOUS_ABUSE','CORRECT_CONFIRM','CORRECT_DISPUTE']
    evidence_ref:str

class ReviewDecision(BaseModel):
    outcome:Literal['REOPENED','VERIFIED_CLOSED']
    evidence_ref:str

def student(session):
    if session['role']!='STUDENT' or not session['verified']:err(403,'Verified student required')

def expire_rounds(c,clock):
    rows=c.execute(select(s.resolution_rounds).where(s.resolution_rounds.c.state=='OPEN')).mappings().all()
    for r in rows:
        if clock<datetime.fromisoformat(r['deadline'].replace('Z','+00:00')):continue
        eligible=c.execute(select(s.voter_eligibility.c.user_id,s.voter_eligibility.c.frozen_weight).where(s.voter_eligibility.c.round_id==r['id'],s.voter_eligibility.c.valid.is_(True))).all()
        votes=c.execute(select(s.resolution_votes.c.choice,s.voter_eligibility.c.frozen_weight).join(s.voter_eligibility,(s.resolution_votes.c.round_id==s.voter_eligibility.c.round_id)&(s.resolution_votes.c.user_id==s.voter_eligibility.c.user_id)).where(s.resolution_votes.c.round_id==r['id'],s.resolution_votes.c.valid.is_(True),s.voter_eligibility.c.valid.is_(True))).all()
        confirms=[v for v in votes if v.choice=='CONFIRM'];disputes=[v for v in votes if v.choice=='DISPUTE'];total=sum(v.frozen_weight for v in eligible)
        close=bool(total and not disputes and sum(v.frozen_weight for v in confirms)>=0.6*total and (len(confirms)>=2 or (len(eligible)==1 and len(confirms)==1)))
        outcome='VERIFIED_CLOSED' if close else 'REVIEW_REQUIRED';ts=clock.isoformat()
        c.execute(update(s.resolution_rounds).where(s.resolution_rounds.c.id==r['id'],s.resolution_rounds.c.state=='OPEN').values(state='FINALIZED',outcome=outcome,finalized_at=ts))
        c.execute(update(s.issues).where(s.issues.c.id==r['issue_id']).values(status=outcome,updated_at=ts,version=s.issues.c.version+1))

def process_expiry(request):
    with immediate_transaction(request.app.state.engine) as c:expire_rounds(c,timestamp(c,request.app.state.config.demo_mode))

@router.get('/me/trust')
def trust(request:Request,session=Depends(get_session)):
    student(session)
    with request.app.state.engine.connect() as c:
        events=c.execute(select(s.trust_events.c.delta,s.trust_events.c.reason,s.trust_events.c.created_at).where(s.trust_events.c.user_id==session['user_id']).order_by(s.trust_events.c.created_at)).mappings()
        return {'score':session['trust_cache'],'events':[dict(e) for e in events]}

@router.post('/admin/adjudicate')
def adjudicate(data:Adjudication,request:Request,session=Depends(get_session)):
    if session['role']!='ADMIN':err(403,'Forbidden')
    if not data.evidence_ref.strip():err(400,'Independent evidence is required')
    with immediate_transaction(request.app.state.engine) as c:
        def award(user,key,delta,reason,source):
            if c.execute(select(s.trust_events.c.id).where(s.trust_events.c.event_key==key)).first():return
            ts=timestamp(c,request.app.state.config.demo_mode).isoformat()
            c.execute(insert(s.trust_events).values(id=str(uuid.uuid4()),user_id=user,event_key=key,delta=delta,reason=reason,source_ref=source,evidence_ref=data.evidence_ref,created_at=ts))
            current=c.execute(select(s.users.c.trust_cache).where(s.users.c.id==user)).scalar_one()
            c.execute(update(s.users).where(s.users.c.id==user).values(trust_cache=max(0,min(100,current+delta))))
        if data.outcome in {'VERIFIED_FIX','VERIFIED_UNRESOLVED'}:
            round_=c.execute(select(s.resolution_rounds).where(s.resolution_rounds.c.id==data.round_ref,s.resolution_rounds.c.state=='FINALIZED')).mappings().first()
            if not round_:err(404,'Not found')
            choice='CONFIRM' if data.outcome=='VERIFIED_FIX' else 'DISPUTE'
            votes=c.execute(select(s.resolution_votes.c.user_id).where(s.resolution_votes.c.round_id==data.round_ref,s.resolution_votes.c.choice==choice,s.resolution_votes.c.valid.is_(True))).scalars()
            for user in votes:award(user,'round:'+data.round_ref+':'+user+':correct',3 if choice=='CONFIRM' else 5,'CORRECT_'+choice,data.round_ref)
        else:
            report=c.execute(select(s.reports.c.owner_id,s.reports.c.visibility,s.reports.c.issue_id).where(s.reports.c.id==data.report_ref)).mappings().first()
            if not report or report['visibility']!='PUBLIC':err(404,'Not found')
            delta={'VERIFIED_REPORT':5,'CONFIRMED_SPAM':-5,'DELIBERATE_FAKE':-15,'MALICIOUS_ABUSE':-20}[data.outcome]
            key=('report:'+str(report['issue_id'])+':'+report['owner_id']+':verified') if data.outcome=='VERIFIED_REPORT' else 'report:'+data.report_ref+':'+data.outcome
            if data.outcome=='VERIFIED_REPORT' and report['issue_id']:
                joined_key='issue:'+report['issue_id']+':'+report['owner_id']+':joined'
                if c.execute(select(s.trust_events.c.id).where(s.trust_events.c.event_key==joined_key)).first():
                    award(report['owner_id'],joined_key+':reversed',-2,'JOIN_REVERSED',report['issue_id'])
            award(report['owner_id'],key,delta,data.outcome,data.report_ref)
            if data.outcome=='VERIFIED_REPORT' and report['issue_id']:
                joined=c.execute(select(s.issue_participants.c.user_id).where(s.issue_participants.c.issue_id==report['issue_id'],s.issue_participants.c.source=='SECOND',s.issue_participants.c.valid.is_(True))).scalars()
                for user in joined:award(user,'issue:'+report['issue_id']+':'+user+':joined',2,'VERIFIED_JOIN',report['issue_id'])
    return {'recorded':True}

@router.post('/admin/adjudicate/reverse')
def reverse_adjudication(data:Reversal,request:Request,session=Depends(get_session)):
    if session['role']!='ADMIN':err(403,'Forbidden')
    if not data.evidence_ref.strip():err(400,'Independent evidence is required')
    with immediate_transaction(request.app.state.engine) as c:
        events=c.execute(select(s.trust_events).where(s.trust_events.c.source_ref==data.source_ref,s.trust_events.c.reason==data.reason)).mappings().all()
        if not events:err(404,'Not found')
        for event in events:
            key='reversal:'+event['id']
            if c.execute(select(s.trust_events.c.id).where(s.trust_events.c.event_key==key)).first():continue
            ts=timestamp(c,request.app.state.config.demo_mode).isoformat()
            c.execute(insert(s.trust_events).values(id=str(uuid.uuid4()),user_id=event['user_id'],event_key=key,delta=-event['delta'],reason='REVERSAL',source_ref=data.source_ref,evidence_ref=data.evidence_ref,created_at=ts))
            current=c.execute(select(s.users.c.trust_cache).where(s.users.c.id==event['user_id'])).scalar_one()
            c.execute(update(s.users).where(s.users.c.id==event['user_id']).values(trust_cache=max(0,min(100,current-event['delta']))))
    return {'recorded':True}

@router.post('/admin/issues/{issue_id}/review')
def review_issue(issue_id:str,data:ReviewDecision,request:Request,session=Depends(get_session)):
    if session['role']!='ADMIN':err(403,'Forbidden')
    if not data.evidence_ref.strip():err(400,'Independent evidence is required')
    with immediate_transaction(request.app.state.engine) as c:
        issue=c.execute(select(s.issues).where(s.issues.c.id==issue_id)).mappings().first()
        if not issue:err(404,'Not found')
        if issue['status']!='REVIEW_REQUIRED':err(409,'Issue is not awaiting review')
        ts=timestamp(c,request.app.state.config.demo_mode).isoformat()
        c.execute(update(s.issues).where(s.issues.c.id==issue_id).values(status=data.outcome,active_since=ts if data.outcome=='REOPENED' else None,updated_at=ts,version=s.issues.c.version+1))
        c.execute(insert(s.issue_history).values(id=str(uuid.uuid4()),issue_id=issue_id,action='ADMIN_REVIEW',status=data.outcome,safe_reason='Independent review recorded',created_at=ts))
        c.execute(insert(s.audit_logs).values(id=str(uuid.uuid4()),event='ADMIN_REVIEW',actor_id=session['user_id'],target_ref=issue_id,safe_reason='Evidence supplied',created_at=ts))
    return {'status':data.outcome}

@router.post('/issues/{issue_id}/vote')
def vote(issue_id:str,data:Vote,request:Request,session=Depends(get_session)):
    student(session)
    with immediate_transaction(request.app.state.engine) as c:
        issue=c.execute(select(s.issues).where(s.issues.c.id==issue_id)).mappings().first()
        if not issue:err(404,'Not found')
        if issue['status'] not in {'REPORTED','ACKNOWLEDGED','IN_PROGRESS','REOPENED'}:err(409,'Issue is not active')
        if c.execute(select(s.reports.c.id).where(s.reports.c.issue_id==issue_id,s.reports.c.owner_id==session['user_id'])).first():err(403,'Reporters cannot vote on their own report')
        old=c.execute(select(s.community_votes.c.choice,s.community_votes.c.valid).where(s.community_votes.c.issue_id==issue_id,s.community_votes.c.user_id==session['user_id'])).mappings().first()
        if old and old['valid'] and old['choice']==data.choice:return {'choice':data.choice}
        ts=timestamp(c,request.app.state.config.demo_mode).isoformat()
        stmt=sqlite_insert(s.community_votes).values(id=str(uuid.uuid4()),issue_id=issue_id,user_id=session['user_id'],choice=data.choice,created_at=ts,updated_at=ts,valid=True)
        c.execute(stmt.on_conflict_do_update(index_elements=['issue_id','user_id'],set_={'choice':data.choice,'updated_at':ts,'valid':True}))
        if data.choice=='2ND':
            stmt=sqlite_insert(s.issue_participants).values(id=str(uuid.uuid4()),issue_id=issue_id,user_id=session['user_id'],source='SECOND',first_joined=ts,valid=True)
            c.execute(stmt.on_conflict_do_update(index_elements=['issue_id','user_id'],set_={'valid':True}))
        else:c.execute(delete(s.issue_participants).where(s.issue_participants.c.issue_id==issue_id,s.issue_participants.c.user_id==session['user_id'],s.issue_participants.c.source=='SECOND'))
        clock=timestamp(c,request.app.state.config.demo_mode)
        recent=c.execute(select(s.community_votes.c.created_at,s.users.c.created_at.label('account_created')).join(s.users,s.users.c.id==s.community_votes.c.user_id).where(s.community_votes.c.issue_id==issue_id,s.community_votes.c.choice==data.choice,s.community_votes.c.valid.is_(True))).all()
        new_accounts=0
        for record in recent:
            try:
                vote_age=(clock-datetime.fromisoformat(record.created_at.replace('Z','+00:00'))).total_seconds()
                account_age=(clock-datetime.fromisoformat(record.account_created.replace('Z','+00:00'))).total_seconds()
                if 0<=vote_age<=60 and 0<=account_age<1800:new_accounts+=1
            except ValueError:continue
        if new_accounts>=3:
            cluster='new-votes:'+issue_id+':'+data.choice+':'+clock.strftime('%Y%m%d%H%M')
            stmt=sqlite_insert(s.moderation_flags).values(id=str(uuid.uuid4()),issue_id=issue_id,rule='NEW_ACCOUNT_VOTE_CLUSTER',cluster_key=cluster,state='PENDING',reason='Recent new-account voting requires review',created_at=ts)
            c.execute(stmt.on_conflict_do_nothing(index_elements=['cluster_key']))
    return {'choice':data.choice}

@router.patch('/staff/issues/{issue_id}')
def transition(issue_id:str,data:Transition,request:Request,session=Depends(get_session)):
    with immediate_transaction(request.app.state.engine) as c:
        issue=c.execute(select(s.issues).where(s.issues.c.id==issue_id)).mappings().first()
        if not issue:err(404,'Not found')
        require_department(session,issue['department_id'])
        if issue['version']!=data.version:err(409,'Stale issue version')
        allowed={'REPORTED':{'ACKNOWLEDGED','IN_PROGRESS','PENDING_VERIFICATION'},'ACKNOWLEDGED':{'IN_PROGRESS','PENDING_VERIFICATION'},'IN_PROGRESS':{'PENDING_VERIFICATION'},'REOPENED':{'IN_PROGRESS','PENDING_VERIFICATION'}}
        if data.status not in allowed.get(issue['status'],set()):err(409,'Invalid transition')
        clock=timestamp(c,request.app.state.config.demo_mode);ts=clock.isoformat()
        changes={'status':data.status,'version':issue['version']+1,'updated_at':ts}
        if data.status=='PENDING_VERIFICATION':
            if issue['active_since']:
                from datetime import datetime
                previous=datetime.fromisoformat(issue['active_since'].replace('Z','+00:00'))
                changes['active_unresolved_seconds']=issue['active_unresolved_seconds']+int(max(0,(clock-previous).total_seconds()))
            changes['active_since']=None
            seq=c.execute(select(func.coalesce(func.max(s.resolution_rounds.c.sequence),0)).where(s.resolution_rounds.c.issue_id==issue_id)).scalar_one()+1
            rid=str(uuid.uuid4());c.execute(insert(s.resolution_rounds).values(id=rid,issue_id=issue_id,sequence=seq,opened_at=ts,deadline=(clock+timedelta(hours=48)).isoformat(),state='OPEN'))
            participants=c.execute(select(s.issue_participants.c.user_id,s.users.c.trust_cache).join(s.users,s.users.c.id==s.issue_participants.c.user_id).where(s.issue_participants.c.issue_id==issue_id,s.issue_participants.c.valid.is_(True))).all()
            for user,trust in participants:c.execute(insert(s.voter_eligibility).values(round_id=rid,user_id=user,frozen_weight=0.5+trust/100,valid=True))
        c.execute(update(s.issues).where(s.issues.c.id==issue_id).values(**changes))
        c.execute(insert(s.issue_history).values(id=str(uuid.uuid4()),issue_id=issue_id,action='STATUS',status=data.status,safe_reason='Staff status update',created_at=ts))
    return {'status':data.status,'version':changes['version']}

@router.post('/issues/{issue_id}/resolution-vote')
def resolution_vote(issue_id:str,data:ResolveVote,request:Request,session=Depends(get_session)):
    student(session)
    process_expiry(request)
    with immediate_transaction(request.app.state.engine) as c:
        round_=c.execute(select(s.resolution_rounds).where(s.resolution_rounds.c.id==data.round_id,s.resolution_rounds.c.issue_id==issue_id)).mappings().first()
        if not round_:err(404,'Not found')
        if round_['state']!='OPEN':err(409,'Round finalized')
        clock=timestamp(c,request.app.state.config.demo_mode)
        from datetime import datetime
        if clock>=datetime.fromisoformat(round_['deadline'].replace('Z','+00:00')):err(409,'Round expired; review required')
        eligible=c.execute(select(s.voter_eligibility).where(s.voter_eligibility.c.round_id==data.round_id,s.voter_eligibility.c.valid.is_(True))).mappings().all()
        if not any(x['user_id']==session['user_id'] for x in eligible):err(403,'Not eligible')
        ts=clock.isoformat();stmt=sqlite_insert(s.resolution_votes).values(id=str(uuid.uuid4()),round_id=data.round_id,user_id=session['user_id'],choice=data.choice,valid=True,created_at=ts,updated_at=ts)
        c.execute(stmt.on_conflict_do_update(index_elements=['round_id','user_id'],set_={'choice':data.choice,'updated_at':ts,'valid':True}))
        votes=c.execute(select(s.resolution_votes.c.choice,s.voter_eligibility.c.frozen_weight).join(s.voter_eligibility,(s.voter_eligibility.c.round_id==s.resolution_votes.c.round_id)&(s.voter_eligibility.c.user_id==s.resolution_votes.c.user_id)).where(s.resolution_votes.c.round_id==data.round_id,s.resolution_votes.c.valid.is_(True),s.voter_eligibility.c.valid.is_(True))).all()
        disputes=[v for v in votes if v.choice=='DISPUTE'];total=sum(v.frozen_weight for v in votes);dw=sum(v.frozen_weight for v in disputes)
        outcome='REVIEW_REQUIRED' if len(eligible)==1 and disputes else 'REOPENED' if len(disputes)>=2 and dw>=1.5 and dw>=0.6*total else 'VERIFIED_CLOSED' if len(votes)==len(eligible) and not disputes and eligible else None
        if outcome:
            c.execute(update(s.resolution_rounds).where(s.resolution_rounds.c.id==data.round_id).values(state='FINALIZED',outcome=outcome,finalized_at=ts))
            c.execute(update(s.issues).where(s.issues.c.id==issue_id).values(status=outcome,active_since=ts if outcome=='REOPENED' else None,updated_at=ts,version=s.issues.c.version+1))
    return {'choice':data.choice,'outcome':outcome}
