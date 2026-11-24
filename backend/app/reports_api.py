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
from app.identity import err, get_session, require_confidential, stamp, now, parse
from app.intelligence import classify_local, location_match, screen, local_details, confidential_details, normalize
from app.issues import publish, timestamp, semantic_suggestion

router=APIRouter(prefix='/api/v1')

class ReportInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    text: str = Field(default='',max_length=5000)
    category_id: str | None = Field(default=None,max_length=36)
    location_id: str | None = Field(default=None,max_length=36)
    location_text: str | None = Field(default=None,max_length=160)
    failure_type: Literal['UNAVAILABLE','SLOW','DAMAGED','OTHER'] | None = None
    asset_identifier: str | None = Field(default=None,pattern=r'^(?i:pc|computer|projector|socket)\s*[-#]?\s*\d{1,4}$',max_length=40)
    visibility: Literal['PUBLIC','CONFIDENTIAL']='PUBLIC'
    merge_issue_id: str | None = Field(default=None,max_length=36)
    create_separate: bool = False
    separation_reason: str | None = Field(default=None,max_length=200)
    attachment_ids: list[str] = Field(default_factory=list,max_length=5)
    @model_validator(mode='after')
    def nonempty(self):
        if not self.text.strip() and not self.category_id and not self.attachment_ids: raise ValueError('Text, category or attachment is required')
        if self.create_separate and not (self.separation_reason or '').strip(): raise ValueError('A reason is required to create a separate issue')
        return self

def student(session):
    if session['role']!='STUDENT' or not session['verified']: err(403,'Verified student required')

def analyze(request,data):
    checks=screen(data.text,data.visibility)
    details=local_details(data.text)
    suggestion=None;selected_subcategory=None;selected_leaf_id=None
    with request.app.state.engine.connect() as conn:
        location,location_error=location_match(conn,data.text,data.location_id,data.location_text)
        category=None
        if data.category_id:
            row=conn.execute(select(s.categories).where(s.categories.c.id==data.category_id,s.categories.c.active.is_(True))).mappings().first()
            if not row: err(400,'Unknown category')
            selected_leaf_id=row['id']
            selected_subcategory=row['code'] if row['parent_id'] else None
            if selected_subcategory=='OTHER':
                parent=conn.execute(select(s.categories).where(s.categories.c.id==row['parent_id'])).mappings().one()
                selected_subcategory=parent['code'] if parent['parent_id'] else 'OTHER'
            while row['parent_id']:
                row=conn.execute(select(s.categories).where(s.categories.c.id==row['parent_id'])).mappings().one()
            category=row['code']
        disabled=conn.execute(select(s.system_settings.c.value).where(s.system_settings.c.key=='provider_unavailable')).scalar()=='true'
    selected_root=category
    if category=='CONDUCT':
        checks['confidential']=True;checks['sensitive']=True;checks['external_safe']=False
    local=classify_local(data.text)
    conflict=bool(category and category!='OTHER' and local and category!=local)
    category=local or (category if category!='OTHER' else None)
    mode='RULES'; ai_status='NOT_USED'; started=time.monotonic()
    if checks['confidential']: category='CONDUCT' if checks['conduct'] or selected_root=='CONDUCT' else (category or 'OTHER')
    if checks['hazard']: category='SAFETY'
    elif (not category or not location) and checks['external_safe'] and not disabled and data.text.strip():
        provider=request.app.state.text_provider
        config=request.app.state.config
        primary=config.azure_model_advanced if len(data.text)>300 else config.azure_model_standard if len(data.text)>120 else config.azure_model_fast
        backup=config.azure_model_standard if primary!=config.azure_model_standard else config.azure_model_advanced
        suggestion,ai_status=provider.classify(data.text,model=primary,timeout=6.0)
        if suggestion is None and ai_status=='FAILED' and time.monotonic()-started<6:
            suggestion,ai_status=provider.classify(data.text,model=backup,timeout=max(0.1,12-(time.monotonic()-started)))
        if suggestion:
            if not category:category=suggestion.category.value
            mode='AI'
            if suggestion.location_candidate and not data.location_text:
                with request.app.state.engine.connect() as conn:
                    location,location_error=location_match(conn,data.text,data.location_id,candidate=suggestion.location_candidate)
    sensitive=checks['sensitive']
    restricted=checks['confidential'] or sensitive
    missing=[]
    if location_error:missing.append(location_error)
    if not category or category=='OTHER':missing.append('Clarify the type of problem')
    if conflict:missing.append('Confirm the category; report and selection differ')
    if checks['hazard_uncertain']:missing.append('Confirm whether the hazard is currently present')
    if sensitive and not checks['confidential']:missing.append('Privacy review required')
    if ai_status in {'FAILED','CIRCUIT_OPEN'} and not category:missing.append('Automatic classification unavailable; select a category')
    if suggestion and suggestion.clarification_required:missing.append('AI requested clarification; confirm the problem details')
    impact='MAJOR_DISRUPTION' if checks['hazard'] else details['impact']
    if impact=='UNKNOWN' and suggestion and suggestion.impact in {'MINOR','PARTIAL_DISRUPTION','COMPLETE_DISRUPTION','MAJOR_DISRUPTION'}:
        impact=suggestion.impact
        missing.append('Confirm the suggested level of disruption')
    if impact=='UNKNOWN' and data.failure_type: impact={'UNAVAILABLE':'COMPLETE_DISRUPTION','SLOW':'PARTIAL_DISRUPTION','DAMAGED':'MINOR','OTHER':'UNKNOWN'}[data.failure_type]
    if impact=='UNKNOWN':missing.append('Clarify the level of disruption')
    subtype=selected_subcategory or details['subcategory']
    if suggestion and not subtype and suggestion.subcategory:
        with request.app.state.engine.connect() as conn:
            root=conn.execute(select(s.categories.c.id).where(s.categories.c.parent_id.is_(None),s.categories.c.code==category)).scalar()
            if root and conn.execute(select(s.categories.c.id).where(s.categories.c.parent_id==root,s.categories.c.code==suggestion.subcategory.upper(),s.categories.c.active.is_(True))).first():subtype=suggestion.subcategory.upper()
    failure=data.failure_type or details['failure_type']
    if not failure and suggestion and suggestion.failure_type in {'UNAVAILABLE','SLOW','DAMAGED','OTHER'}:failure=suggestion.failure_type
    asset=data.asset_identifier or details['asset_identifier']
    if not asset and suggestion and suggestion.asset_identifier and normalize(suggestion.asset_identifier) in normalize(data.text):asset=suggestion.asset_identifier
    if (checks['hazard'] and selected_root!='SAFETY') or (checks['conduct'] and selected_root not in {None,'CONDUCT'}):
        subtype=None;selected_leaf_id=None
    label=(subtype or category or 'problem').replace('_',' ').lower()
    reason=('Potential safety hazard requires urgent attention' if checks['hazard'] else f"{label.capitalize()} reported; disruption: {impact.replace('_',' ').lower()}")
    return {'category':category or 'OTHER','selected_category_id':selected_leaf_id,'subcategory':subtype,'failure_type':failure,'asset_identifier':asset,'impact':impact,
            'department':location['department_id'] if location and not missing else None,
            'location_id':location['id'] if location else None,'location':location['name'] if location else None,
            'priority_proposal':100 if checks['hazard'] else None,
            'reason':reason,
            'emergency_guidance':'Move away from danger and contact the appropriate emergency services.' if checks['hazard'] else None,
            'visibility':'CONFIDENTIAL' if checks['confidential'] else 'RESTRICTED' if restricted else 'PUBLIC',
            'clarification_required':bool(missing),'clarifications':missing,'processing_mode':mode,'provider_status':ai_status,
            'privacy_screen':checks,'latency_ms':int((time.monotonic()-started)*1000)}

def public_result(result):
    return {k:v for k,v in result.items() if k not in {'privacy_screen','latency_ms'}}

def safe_case_content(result, raw_text):
    return f"{confidential_details(raw_text)}. Location: {result['location'] or 'unconfirmed'}. Further detail may require confidential follow-up."

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
        if len(data.attachment_ids)!=len(set(data.attachment_ids)):err(400,'Duplicate attachment')
        extracted=[];total=0
        for attachment_id in data.attachment_ids:
            attachment=conn.execute(select(s.attachments).where(s.attachments.c.id==attachment_id,s.attachments.c.owner_id==session['user_id'],s.attachments.c.report_id.is_(None),s.attachments.c.case_id.is_(None))).mappings().first()
            if not attachment or (attachment['expires_at'] and parse(attachment['expires_at'])<=now()):err(404,'Attachment not found')
            total+=attachment['size']
            if total>25*1024*1024:err(413,'Attachments too large')
            if attachment['purpose']=='MAIN_COMPLAINT' and attachment['safe_type'] in {'PDF','TXT'}:
                from app.attachments import safe_path
                extracted.append(safe_path(request,attachment['sanitized_key']).read_text(encoding='utf-8')[:5000])
        if extracted:data=data.model_copy(update={'text':(data.text+'\n'+'\n'.join(extracted))[:5000]})
    result=analyze(request,data); report_id=str(uuid.uuid4());case_id=None;ts=stamp(now())
    suggestion=semantic_suggestion(request,result,data.text) if not data.merge_issue_id and not data.create_separate else None
    with immediate_transaction(request.app.state.engine) as conn:
        old=conn.execute(select(s.reports.c.id,s.reports.c.case_id,s.reports.c.clarification_state).where(s.reports.c.owner_id==session['user_id'],s.reports.c.request_key==idempotency_key)).mappings().first()
        if old:return {'reference':old['id'],'status':'CLARIFICATION_REQUIRED' if old['clarification_state']=='REQUIRED' else 'PENDING','confidential':bool(old['case_id'])}
        if result['visibility'] in {'CONFIDENTIAL','RESTRICTED'}:
            case_id=str(uuid.uuid4())
            conn.execute(insert(s.confidential_cases).values(id=case_id,safe_content=safe_case_content(result,data.text),status='OPEN',hazard='SAFETY' if result['priority_proposal']==100 else 'NONE',created_at=ts,updated_at=ts))
            conn.execute(insert(s.confidential_ownership).values(case_id=case_id,user_id=session['user_id']))
        clean=public_result(result)
        conn.execute(insert(s.reports).values(id=report_id,owner_id=session['user_id'],case_id=case_id,visibility=result['visibility'],private_input=data.text,safe_extracted_fields=json.dumps(clean),clarification_state='REQUIRED' if result['clarification_required'] else 'NONE',created_at=ts,request_key=idempotency_key))
        if len(data.attachment_ids)!=len(set(data.attachment_ids)):err(400,'Duplicate attachment')
        total=0
        for attachment_id in data.attachment_ids:
            attachment=conn.execute(select(s.attachments).where(s.attachments.c.id==attachment_id,s.attachments.c.owner_id==session['user_id'],s.attachments.c.report_id.is_(None),s.attachments.c.case_id.is_(None))).mappings().first()
            if not attachment or (attachment['expires_at'] and parse(attachment['expires_at'])<=now()):err(404,'Attachment not found')
            total+=attachment['size']
            if total>25*1024*1024:err(413,'Attachments too large')
            if case_id:conn.execute(update(s.attachments).where(s.attachments.c.id==attachment_id).values(case_id=case_id,state='PRIVATE'))
            else:conn.execute(update(s.attachments).where(s.attachments.c.id==attachment_id).values(report_id=report_id))
        conn.execute(insert(s.processing_events).values(id=str(uuid.uuid4()),report_id=report_id,kind='classification',mode=result['processing_mode'],provider_label='azure' if result['processing_mode']=='AI' else None,success=True,error_class=result['provider_status'] if result['provider_status'] in {'FAILED','CIRCUIT_OPEN'} else None,latency_ms=result['latency_ms'],created_at=ts))
        issue_id,candidates=publish(conn,report_id,session['user_id'],result,timestamp(conn,request.app.state.config.demo_mode),data.merge_issue_id or suggestion,data.create_separate)
        if candidates:conn.execute(update(s.reports).where(s.reports.c.id==report_id).values(clarification_state='REQUIRED'))
    return {'reference':report_id,'issue_id':issue_id,'candidates':candidates,'status':'CLARIFICATION_REQUIRED' if result['clarification_required'] or candidates else 'PENDING','confidential':bool(case_id),'proposal':clean}

@router.patch('/reports/{report_id}/clarification')
def clarify(report_id:str,data:ReportInput,request:Request,session=Depends(get_session)):
    student(session)
    with request.app.state.engine.connect() as conn:
        existing=conn.execute(select(s.reports.c.id,s.reports.c.case_id,s.reports.c.visibility,s.reports.c.issue_id).where(s.reports.c.id==report_id,s.reports.c.owner_id==session['user_id'])).mappings().first()
        if not existing:err(404,'Not found')
        if existing['issue_id']:err(409,'Published reports cannot be reclassified here')
    if existing['case_id']:
        data=data.model_copy(update={'visibility':'CONFIDENTIAL'})
    result=analyze(request,data);ts=stamp(now())
    suggestion=semantic_suggestion(request,result,data.text) if not data.merge_issue_id and not data.create_separate else None
    with immediate_transaction(request.app.state.engine) as conn:
        existing=conn.execute(select(s.reports.c.case_id).where(s.reports.c.id==report_id,s.reports.c.owner_id==session['user_id'])).mappings().first()
        if not existing:err(404,'Not found')
        case_id=existing['case_id']
        if not case_id and result['visibility'] in {'CONFIDENTIAL','RESTRICTED'}:
            case_id=str(uuid.uuid4())
            conn.execute(insert(s.confidential_cases).values(id=case_id,safe_content=safe_case_content(result,data.text),status='OPEN',hazard='SAFETY' if result['priority_proposal']==100 else 'NONE',created_at=ts,updated_at=ts))
            conn.execute(insert(s.confidential_ownership).values(case_id=case_id,user_id=session['user_id']))
        elif case_id:
            conn.execute(update(s.confidential_cases).where(s.confidential_cases.c.id==case_id).values(safe_content=safe_case_content(result,data.text),hazard='SAFETY' if result['priority_proposal']==100 else 'NONE',updated_at=ts))
        clean=public_result(result)
        conn.execute(update(s.reports).where(s.reports.c.id==report_id).values(case_id=case_id,visibility=result['visibility'],private_input=data.text,safe_extracted_fields=json.dumps(clean),clarification_state='REQUIRED' if result['clarification_required'] else 'RESOLVED'))
        conn.execute(insert(s.processing_events).values(id=str(uuid.uuid4()),report_id=report_id,kind='clarification',mode=result['processing_mode'],provider_label='azure' if result['processing_mode']=='AI' else None,success=True,error_class=result['provider_status'] if result['provider_status'] in {'FAILED','CIRCUIT_OPEN'} else None,latency_ms=result['latency_ms'],created_at=ts))
        issue_id,candidates=publish(conn,report_id,session['user_id'],result,timestamp(conn,request.app.state.config.demo_mode),data.merge_issue_id or suggestion,data.create_separate)
        if candidates:conn.execute(update(s.reports).where(s.reports.c.id==report_id).values(clarification_state='REQUIRED'))
    return {'reference':report_id,'issue_id':issue_id,'candidates':candidates,'status':'CLARIFICATION_REQUIRED' if result['clarification_required'] or candidates else 'PENDING','confidential':bool(case_id),'proposal':clean}

@router.get('/me/reports')
def my_reports(request:Request,session=Depends(get_session)):
    student(session)
    with request.app.state.engine.connect() as conn:
        rows=conn.execute(select(s.reports.c.id,s.reports.c.issue_id,s.reports.c.case_id,s.reports.c.created_at,s.reports.c.clarification_state,s.reports.c.safe_extracted_fields,s.reports.c.private_input).where(s.reports.c.owner_id==session['user_id']).order_by(s.reports.c.created_at.desc())).mappings()
        reports=[{'reference':r['id'],'issue_id':r['issue_id'],'confidential':bool(r['case_id']),'created_at':r['created_at'],'clarification_state':r['clarification_state'],'description':r['private_input'],'proposal':json.loads(r['safe_extracted_fields']) if r['safe_extracted_fields'] else None} for r in rows]
        joined=conn.execute(select(s.issue_participants.c.issue_id,s.issue_participants.c.first_joined).where(s.issue_participants.c.user_id==session['user_id'],s.issue_participants.c.source=='SECOND',s.issue_participants.c.valid.is_(True))).mappings()
        reports.extend({'reference':None,'issue_id':r['issue_id'],'confidential':False,'created_at':r['first_joined'],'clarification_state':'NONE','description':None,'proposal':None} for r in joined)
        return reports

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
