import json
import time
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import insert, select, update
from app import schema as s
from app.azure_provider import AzureTextProvider
from app.database import immediate_transaction
from app.identity import err, get_session, require_confidential, stamp, now
from app.intelligence import classify_local, location_match, screen

router=APIRouter(prefix='/api/v1')

class ReportInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    text: str = Field(default='',max_length=5000)
    category_id: str | None = Field(default=None,max_length=36)
    location_id: str | None = Field(default=None,max_length=36)
    location_text: str | None = Field(default=None,max_length=160)
    visibility: Literal['PUBLIC','CONFIDENTIAL']='PUBLIC'
    @model_validator(mode='after')
    def nonempty(self):
        if not self.text.strip() and not self.category_id: raise ValueError('Text or category is required')
        return self

def student(session):
    if session['role']!='STUDENT' or not session['verified']: err(403,'Verified student required')

def analyze(request,data):
    checks=screen(data.text,data.visibility)
    with request.app.state.engine.connect() as conn:
        location,location_error=location_match(conn,data.text,data.location_id,data.location_text)
        category=None
        if data.category_id:
            row=conn.execute(select(s.categories).where(s.categories.c.id==data.category_id,s.categories.c.active.is_(True))).mappings().first()
            if not row: err(400,'Unknown category')
            while row['parent_id']:
                row=conn.execute(select(s.categories).where(s.categories.c.id==row['parent_id'])).mappings().one()
            category=row['code']
        disabled=conn.execute(select(s.system_settings.c.value).where(s.system_settings.c.key=='provider_unavailable')).scalar()=='true'
    if category=='CONDUCT':
        checks['confidential']=True;checks['sensitive']=True;checks['external_safe']=False
    local=classify_local(data.text)
    conflict=bool(category and category!='OTHER' and local and category!=local)
    category=local or (category if category!='OTHER' else None)
    mode='RULES'; ai_status='NOT_USED'; started=time.monotonic()
    if checks['confidential']: category='CONDUCT' if data.visibility=='PUBLIC' else (category or 'OTHER')
    elif checks['hazard']: category='SAFETY'
    elif not category and checks['external_safe'] and not disabled:
        provider=request.app.state.text_provider
        config=request.app.state.config
        primary=config.azure_model_advanced if len(data.text)>300 else config.azure_model_standard if len(data.text)>120 else config.azure_model_fast
        backup=config.azure_model_standard if primary!=config.azure_model_standard else config.azure_model_advanced
        suggestion,ai_status=provider.classify(data.text,model=primary,timeout=6.0)
        if suggestion is None and ai_status=='FAILED' and time.monotonic()-started<6:
            suggestion,ai_status=provider.classify(data.text,model=backup,timeout=max(0.1,12-(time.monotonic()-started)))
        if suggestion:
            category=suggestion.category.value;mode='AI'
    # Unrecognized or potentially identifying free text stays restricted until
    # a human can review it; a known infrastructure keyword is not clearance.
    sensitive=checks['sensitive'] or (bool(data.text.strip()) and not checks['external_safe'])
    restricted=checks['confidential'] or sensitive
    missing=[]
    if location_error:missing.append(location_error)
    if not category:missing.append('Clarify the type of problem')
    if conflict:missing.append('Confirm the category; report and selection differ')
    if checks['hazard_uncertain']:missing.append('Confirm whether the hazard is currently present')
    if sensitive and not checks['confidential']:missing.append('Privacy review required')
    if ai_status in {'FAILED','CIRCUIT_OPEN'} and not category:missing.append('Automatic classification unavailable; select a category')
    return {'category':category or 'OTHER','department':location['department_id'] if location else None,
            'location_id':location['id'] if location else None,'location':location['name'] if location else None,
            'priority_proposal':100 if checks['hazard'] else None,
            'reason':'Potential safety hazard requires urgent attention' if checks['hazard'] else 'Report requires classification and review',
            'emergency_guidance':'Move away from danger and contact the appropriate emergency services.' if checks['hazard'] else None,
            'visibility':'CONFIDENTIAL' if checks['confidential'] else 'RESTRICTED' if restricted else 'PUBLIC',
            'clarification_required':bool(missing),'clarifications':missing,'processing_mode':mode,'provider_status':ai_status,
            'privacy_screen':checks,'latency_ms':int((time.monotonic()-started)*1000)}

def public_result(result):
    return {k:v for k,v in result.items() if k not in {'privacy_screen','latency_ms'}}

def safe_case_content(result):
    return f"Category: {result['category']}; location: {result['location'] or 'unconfirmed'}; hazard: {'potential safety hazard' if result['priority_proposal']==100 else 'not identified'}."

@router.post('/reports/preview')
def preview(data:ReportInput,request:Request,session=Depends(get_session)):
    student(session)
    return public_result(analyze(request,data))

@router.post('/reports')
def submit(data:ReportInput,request:Request,session=Depends(get_session),idempotency_key:str=Header(default='',max_length=128)):
    student(session)
    if not idempotency_key:err(400,'Idempotency-Key required')
    with request.app.state.engine.connect() as conn:
        old=conn.execute(select(s.reports.c.id,s.reports.c.case_id,s.reports.c.clarification_state).where(s.reports.c.owner_id==session['user_id'],s.reports.c.request_key==idempotency_key)).mappings().first()
        if old:return {'reference':old['id'],'status':'CLARIFICATION_REQUIRED' if old['clarification_state']=='REQUIRED' else 'PENDING','confidential':bool(old['case_id'])}
    result=analyze(request,data); report_id=str(uuid.uuid4());case_id=None;ts=stamp(now())
    with immediate_transaction(request.app.state.engine) as conn:
        old=conn.execute(select(s.reports.c.id,s.reports.c.case_id,s.reports.c.clarification_state).where(s.reports.c.owner_id==session['user_id'],s.reports.c.request_key==idempotency_key)).mappings().first()
        if old:return {'reference':old['id'],'status':'CLARIFICATION_REQUIRED' if old['clarification_state']=='REQUIRED' else 'PENDING','confidential':bool(old['case_id'])}
        if result['visibility'] in {'CONFIDENTIAL','RESTRICTED'}:
            case_id=str(uuid.uuid4())
            conn.execute(insert(s.confidential_cases).values(id=case_id,safe_content=safe_case_content(result),status='OPEN',hazard='SAFETY' if result['priority_proposal']==100 else 'NONE',created_at=ts,updated_at=ts))
            conn.execute(insert(s.confidential_ownership).values(case_id=case_id,user_id=session['user_id']))
        clean=public_result(result)
        conn.execute(insert(s.reports).values(id=report_id,owner_id=session['user_id'],case_id=case_id,visibility=result['visibility'],private_input=data.text,safe_extracted_fields=json.dumps(clean),clarification_state='REQUIRED' if result['clarification_required'] else 'NONE',created_at=ts,request_key=idempotency_key))
        conn.execute(insert(s.processing_events).values(id=str(uuid.uuid4()),report_id=report_id,kind='classification',mode=result['processing_mode'],provider_label='azure' if result['processing_mode']=='AI' else None,success=True,error_class=result['provider_status'] if result['provider_status'] in {'FAILED','CIRCUIT_OPEN'} else None,latency_ms=result['latency_ms'],created_at=ts))
    return {'reference':report_id,'status':'CLARIFICATION_REQUIRED' if result['clarification_required'] else 'PENDING','confidential':bool(case_id),'proposal':clean}

@router.patch('/reports/{report_id}/clarification')
def clarify(report_id:str,data:ReportInput,request:Request,session=Depends(get_session)):
    student(session)
    with request.app.state.engine.connect() as conn:
        existing=conn.execute(select(s.reports.c.id,s.reports.c.case_id,s.reports.c.visibility).where(s.reports.c.id==report_id,s.reports.c.owner_id==session['user_id'])).mappings().first()
        if not existing:err(404,'Not found')
    if existing['case_id']:
        data=data.model_copy(update={'visibility':'CONFIDENTIAL'})
    result=analyze(request,data);ts=stamp(now())
    with immediate_transaction(request.app.state.engine) as conn:
        existing=conn.execute(select(s.reports.c.case_id).where(s.reports.c.id==report_id,s.reports.c.owner_id==session['user_id'])).mappings().first()
        if not existing:err(404,'Not found')
        case_id=existing['case_id']
        if not case_id and result['visibility'] in {'CONFIDENTIAL','RESTRICTED'}:
            case_id=str(uuid.uuid4())
            conn.execute(insert(s.confidential_cases).values(id=case_id,safe_content=safe_case_content(result),status='OPEN',hazard='SAFETY' if result['priority_proposal']==100 else 'NONE',created_at=ts,updated_at=ts))
            conn.execute(insert(s.confidential_ownership).values(case_id=case_id,user_id=session['user_id']))
        elif case_id:
            conn.execute(update(s.confidential_cases).where(s.confidential_cases.c.id==case_id).values(safe_content=safe_case_content(result),hazard='SAFETY' if result['priority_proposal']==100 else 'NONE',updated_at=ts))
        clean=public_result(result)
        conn.execute(update(s.reports).where(s.reports.c.id==report_id).values(case_id=case_id,visibility=result['visibility'],private_input=data.text,safe_extracted_fields=json.dumps(clean),clarification_state='REQUIRED' if result['clarification_required'] else 'RESOLVED'))
        conn.execute(insert(s.processing_events).values(id=str(uuid.uuid4()),report_id=report_id,kind='clarification',mode=result['processing_mode'],provider_label='azure' if result['processing_mode']=='AI' else None,success=True,error_class=result['provider_status'] if result['provider_status'] in {'FAILED','CIRCUIT_OPEN'} else None,latency_ms=result['latency_ms'],created_at=ts))
    return {'reference':report_id,'status':'CLARIFICATION_REQUIRED' if result['clarification_required'] else 'PENDING','confidential':bool(case_id),'proposal':clean}

@router.get('/me/reports')
def my_reports(request:Request,session=Depends(get_session)):
    student(session)
    with request.app.state.engine.connect() as conn:
        rows=conn.execute(select(s.reports.c.id,s.reports.c.case_id,s.reports.c.created_at,s.reports.c.clarification_state,s.reports.c.safe_extracted_fields,s.reports.c.private_input).where(s.reports.c.owner_id==session['user_id']).order_by(s.reports.c.created_at.desc())).mappings()
        return [{'reference':r['id'],'confidential':bool(r['case_id']),'created_at':r['created_at'],'clarification_state':r['clarification_state'],'description':r['private_input'],'proposal':json.loads(r['safe_extracted_fields']) if r['safe_extracted_fields'] else None} for r in rows]

@router.get('/admin/confidential')
def confidential_inbox(request:Request,session=Depends(get_session)):
    require_confidential(session)
    with request.app.state.engine.connect() as conn:
        rows=conn.execute(select(s.confidential_cases.c.id,s.confidential_cases.c.safe_content,s.confidential_cases.c.status,s.confidential_cases.c.hazard,s.confidential_cases.c.created_at)).mappings()
        return [dict(r) for r in rows]

class CaseUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    status:Literal['OPEN','IN_REVIEW','CLOSED']

@router.patch('/admin/confidential/{case_id}')
def update_case(case_id:str,data:CaseUpdate,request:Request,session=Depends(get_session)):
    require_confidential(session)
    with immediate_transaction(request.app.state.engine) as conn:
        result=conn.execute(update(s.confidential_cases).where(s.confidential_cases.c.id==case_id).values(status=data.status,updated_at=stamp(now())))
        if not result.rowcount:err(404,'Not found')
    return {'reference':case_id,'status':data.status}
