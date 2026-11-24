"""Actual aggregate dashboard data and optional AI narrative."""
import math
from datetime import timedelta,datetime
from fastapi import APIRouter,Depends,Request
from sqlalchemy import select,func
from app import schema as s
from app.identity import err,get_session
from app.issues import timestamp,issue_dto

router=APIRouter(prefix='/api/v1')

@router.get('/trending')
def trending(request:Request,session=Depends(get_session)):
    with request.app.state.engine.connect() as conn:
        clock=timestamp(conn,request.app.state.config.demo_mode)
        issues=conn.execute(select(s.issues).where(s.issues.c.status!='VERIFIED_CLOSED')).mappings().all()
        result=[]
        for issue in issues:
            participants=conn.execute(select(s.issue_participants.c.first_joined,s.users.c.trust_cache).join(s.users,s.users.c.id==s.issue_participants.c.user_id).where(s.issue_participants.c.issue_id==issue['id'],s.issue_participants.c.valid.is_(True))).all()
            score=0
            for participant in participants:
                age=(clock-datetime.fromisoformat(participant.first_joined.replace('Z','+00:00'))).total_seconds()/3600
                if 0<=age<48:score+=(0.5+participant.trust_cache/100)*(1 if age<24 else .5)
            dto=issue_dto(conn,dict(issue),clock,session['user_id']);dto['trend_score']=round(score,2);result.append(dto)
    return sorted(result,key=lambda x:(-x['trend_score'],-x['affected_count'],x['id']))[:100]

@router.get('/admin/statistics')
def statistics(request:Request,session=Depends(get_session)):
    if session['role']!='ADMIN':err(403,'Forbidden')
    with request.app.state.engine.connect() as conn:
        issues=conn.execute(select(s.issues.c.department_id,s.issues.c.status,s.issues.c.hazard,s.issues.c.category_id)).mappings().all()
        processing=conn.execute(select(s.processing_events.c.mode,func.count()).group_by(s.processing_events.c.mode)).all()
    by_department={};by_status={};by_category={}
    for issue in issues:
        for target,key in [(by_department,issue['department_id']),(by_status,issue['status']),(by_category,issue['category_id'])]:target[key]=target.get(key,0)+1
    return {'total':len(issues),'critical':sum(x['hazard'] in {'SAFETY','MEDICAL'} and x['status']!='VERIFIED_CLOSED' for x in issues),'departments':by_department,'statuses':by_status,'categories':by_category,'processing':dict(processing)}

@router.post('/admin/summary')
def summary(request:Request,session=Depends(get_session)):
    stats=statistics(request,session)
    fallback=f"There are {stats['total']} ordinary issues, including {stats['critical']} unresolved safety issues. Review critical and reopened cases first."
    if not request.app.state.config.azure_enabled:return {'source':'conventional','summary':fallback,'statistics':stats}
    with request.app.state.engine.connect() as conn:
        disabled=conn.execute(select(s.system_settings.c.value).where(s.system_settings.c.key=='provider_unavailable')).scalar()=='true'
    if disabled:return {'source':'conventional','summary':fallback,'statistics':stats}
    try:
        result=request.app.state.text_provider._ask('Return JSON with one key summary containing a short qualitative administrative recommendation. Use only these aggregate statistics; do not invent numbers or facts.',stats,request.app.state.config.azure_model_fast,timeout=6)
        narrative=result.get('summary') if isinstance(result,dict) else None
        if not isinstance(narrative,str) or not narrative.strip() or any(c.isdigit() for c in narrative):raise ValueError('Unverified summary')
        return {'source':'AI','summary':narrative[:800],'statistics':stats}
    except Exception:return {'source':'conventional','summary':fallback,'statistics':stats}

@router.get('/admin/moderation')
def moderation(request:Request,session=Depends(get_session)):
    if session['role']!='ADMIN':err(403,'Forbidden')
    with request.app.state.engine.connect() as conn:
        flags=conn.execute(select(s.moderation_flags.c.id,s.moderation_flags.c.rule,s.moderation_flags.c.state,s.moderation_flags.c.reason,s.moderation_flags.c.created_at)).mappings().all()
    return [dict(row) for row in flags]
