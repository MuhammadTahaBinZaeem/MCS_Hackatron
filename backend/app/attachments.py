"""Private staged attachments; public access requires explicit human review."""
import hashlib
import io
import subprocess
import sys
import os
import uuid
import json
import base64
from datetime import timedelta
from pathlib import Path
from typing import Literal
from fastapi import APIRouter,Depends,File,Form,Request,UploadFile
from fastapi.responses import Response
from PIL import Image,ImageOps,UnidentifiedImageError
from sqlalchemy import insert,select,update,delete
from app import schema as s
from app.database import immediate_transaction
from app.identity import err,get_session,now,stamp,parse
from dotenv import dotenv_values
import httpx

router=APIRouter(prefix='/api/v1')
EXT={'.jpg':'JPEG','.jpeg':'JPEG','.png':'PNG','.webp':'WEBP','.pdf':'PDF','.txt':'TXT'}
MIME={'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp','PDF':'application/pdf','TXT':'text/plain; charset=utf-8'}
Image.MAX_IMAGE_PIXELS=40_000_000

def detect_faces(image_bytes):
    """Optional local YuNet; absent dependencies/model always require review."""
    model=os.environ.get('FACE_MODEL_PATH','')
    if not model or not Path(model).is_file():return 'NOT_CONFIGURED'
    try:
        import cv2
        import numpy as np
        image=cv2.imdecode(np.frombuffer(image_bytes,dtype=np.uint8),cv2.IMREAD_COLOR)
        if image is None:return 'NOT_CONFIGURED'
        h,w=image.shape[:2]
        detector=cv2.FaceDetectorYN.create(model,'',(w,h))
        _,faces=detector.detect(image)
        return 'DETECTED' if faces is not None and len(faces) else 'CLEAR'
    except Exception:return 'NOT_CONFIGURED'

def featherless_screen(image_bytes, credential_file):
    """Send only explicitly consented, user-declared non-sensitive images."""
    try:
        values=dotenv_values(credential_file);key=values.get('FEATHERLESS_API_KEY','')
        if not key:return 'NOT_CONFIGURED'
        payload={'model':'Qwen/Qwen3-VL-4B-Instruct','messages':[{'role':'user','content':[{'type':'text','text':'Is any human face visible in this image? Reply with exactly JSON: {"face_visible": true} or {"face_visible": false}.'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(image_bytes).decode()}}]}],'max_tokens':128,'temperature':0}
        response=httpx.post('https://api.featherless.ai/v1/chat/completions',headers={'Authorization':'Bearer '+key},json=payload,timeout=12)
        response.raise_for_status();text=response.json()['choices'][0]['message']['content']
        start=text.find('{');end=text.rfind('}')
        parsed=json.loads(text[start:end+1]);visible=parsed.get('face_visible')
        if type(visible) is not bool:return 'NOT_CONFIGURED'
        return 'DETECTED' if visible else 'CLEAR'
    except Exception:return 'NOT_CONFIGURED'

def upload_dir(request):
    root=request.app.state.config.runtime_dir.resolve();path=root/'uploads'
    if path.is_symlink():err(400,'Invalid storage directory')
    path.mkdir(mode=0o700,exist_ok=True)
    if path.resolve().parent!=root:err(400,'Invalid storage directory')
    return path

def safe_path(request,key):
    if not key or not key.isalnum():err(404,'Not found')
    root=upload_dir(request);path=root/key
    if path.is_symlink() or path.resolve().parent!=root.resolve():err(404,'Not found')
    return path

def cleanup_expired(request):
    with immediate_transaction(request.app.state.engine) as c:
        rows=c.execute(select(s.attachments).where(s.attachments.c.report_id.is_(None),s.attachments.c.case_id.is_(None),s.attachments.c.expires_at.is_not(None))).mappings().all()
        for row in rows:
            if parse(row['expires_at'])<=now():
                safe_path(request,row['private_storage_key']).unlink(missing_ok=True)
                if row['sanitized_key']:safe_path(request,row['sanitized_key']).unlink(missing_ok=True)
                c.execute(delete(s.attachment_reviews).where(s.attachment_reviews.c.attachment_id==row['id']))
                c.execute(delete(s.attachments).where(s.attachments.c.id==row['id']))

@router.post('/attachments')
async def upload(request:Request,file:UploadFile=File(...),purpose:Literal['MAIN_COMPLAINT','SUPPORTING_EVIDENCE']=Form(...),faces:Literal['YES','NO','UNSURE']=Form(...),nsfw:Literal['YES','NO','UNSURE']=Form(...),sensitive:Literal['YES','NO','UNSURE']=Form(...),public_requested:bool=Form(False),external_consent:bool=Form(False),report_visibility:Literal['PUBLIC','CONFIDENTIAL']=Form('CONFIDENTIAL'),session=Depends(get_session)):
    if session['role']!='STUDENT' or not session['verified']:err(403,'Verified student required')
    cleanup_expired(request)
    filename=file.filename or ''
    if '/' in filename or '\\' in filename or filename in {'.','..'}:err(400,'Invalid filename')
    kind=EXT.get(Path(filename).suffix.lower())
    if not kind:err(415,'Unsupported type')
    limit=1024*1024 if kind=='TXT' else 10*1024*1024
    raw=await file.read(limit+1)
    if len(raw)>limit:err(413,'File too large')
    if not raw:err(400,'Empty file')
    derived=None
    try:
        if kind in {'JPEG','PNG','WEBP'}:
            with Image.open(io.BytesIO(raw)) as image:
                if image.format!=kind:err(415,'Type mismatch')
                if image.width * image.height > 40_000_000:err(413,'Image too large')
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                clean=ImageOps.exif_transpose(image).convert('RGB' if kind=='JPEG' else 'RGBA')
                buf=io.BytesIO();clean.save(buf,format=kind);derived=buf.getvalue()
        elif kind=='PDF':
            if not raw.startswith(b'%PDF-'):err(415,'Type mismatch')
            script="import io,sys; from pypdf import PdfReader; p=PdfReader(io.BytesIO(sys.stdin.buffer.read()),strict=True); assert not p.is_encrypted and len(p.pages)<=20; t='\\n'.join(x.extract_text() or '' for x in p.pages); sys.stdout.buffer.write(t[:1000000].encode('utf-8'))"
            process=subprocess.run([sys.executable,'-c',script],input=raw,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=8,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if process.returncode:err(400,'Unsupported PDF')
            derived=process.stdout
        else:
            decoded=raw.decode('utf-8')
            if '\x00' in decoded:err(415,'Type mismatch')
            derived=decoded.encode('utf-8')
    except (UnidentifiedImageError,OSError,ValueError,UnicodeError,Image.DecompressionBombError):err(400,'Invalid or unsafe file')
    except Exception as exc:
        from fastapi import HTTPException
        if isinstance(exc,HTTPException):raise
        err(400,'Invalid or unsafe file')
    detection='NOT_CONFIGURED'
    if kind in {'JPEG','PNG','WEBP'} and external_consent and report_visibility=='PUBLIC' and faces!='YES' and nsfw=='NO' and sensitive=='NO':
        png=io.BytesIO()
        with Image.open(io.BytesIO(derived)) as image:image.save(png,format='PNG')
        detection=featherless_screen(png.getvalue(),request.app.state.config.azure_credential_file)
    key=uuid.uuid4().hex;clean_key=uuid.uuid4().hex;file_path=safe_path(request,key);derived_path=safe_path(request,clean_key)
    try:
        file_path.write_bytes(raw);derived_path.write_bytes(derived)
        with immediate_transaction(request.app.state.engine) as c:
            c.execute(insert(s.attachments).values(id=key,owner_id=session['user_id'],purpose=purpose,safe_type=kind,size=len(raw),checksum=hashlib.sha256(raw).hexdigest(),private_storage_key=key,sanitized_key=clean_key,declared_faces=faces,declared_nsfw=nsfw,declared_sensitive=sensitive,public_requested=public_requested,external_consent=external_consent,state='PENDING_REVIEW' if public_requested and detection!='DETECTED' else 'PRIVATE',expires_at=stamp(now()+timedelta(hours=24)),created_at=stamp(now()),updated_at=stamp(now())))
            c.execute(insert(s.attachment_reviews).values(id=str(uuid.uuid4()),attachment_id=key,local_face_result=detection,review_flags='local detector',created_at=stamp(now())))
    except BaseException:
        file_path.unlink(missing_ok=True);derived_path.unlink(missing_ok=True);raise
    return {'id':key,'state':'PENDING_REVIEW' if public_requested and detection!='DETECTED' else 'PRIVATE','face_detection':detection}

@router.get('/attachments/{attachment_id}')
def retrieve(attachment_id:str,request:Request,session=Depends(get_session)):
    with request.app.state.engine.connect() as c:
        item=c.execute(select(s.attachments).where(s.attachments.c.id==attachment_id)).mappings().first()
    if not item:err(404,'Not found')
    public=False
    if item['state']=='PUBLIC_APPROVED' and item['public_requested'] and item['case_id'] is None and item['report_id']:
        with request.app.state.engine.connect() as c:
            report=c.execute(select(s.reports.c.visibility,s.reports.c.issue_id).where(s.reports.c.id==item['report_id'])).mappings().first()
        public=bool(report and report['visibility']=='PUBLIC' and report['issue_id'])
    owner=item['owner_id']==session['user_id']
    authorized=False
    if item['case_id']:
        authorized=bool(session['confidential_capability'])
    elif item['report_id']:
        with request.app.state.engine.connect() as c:
            assigned=c.execute(select(s.issues.c.department_id).join(s.reports,s.reports.c.issue_id==s.issues.c.id).where(s.reports.c.id==item['report_id'])).scalar()
            detected=c.execute(select(s.attachment_reviews.c.id).where(s.attachment_reviews.c.attachment_id==attachment_id,s.attachment_reviews.c.local_face_result=='DETECTED')).first()
        authorized=session['role']=='ADMIN' or (session['role']=='STAFF' and not detected and assigned==session['department_id'] and item['declared_faces']=='NO' and item['declared_nsfw']=='NO' and item['declared_sensitive']=='NO')
    if not (public or owner or authorized):err(404,'Not found')
    if item['state'] in {'QUARANTINED','REJECTED'}:err(404,'Not found')
    # All public bytes are sanitized. PDF derivatives are extracted text.
    key=item['sanitized_key'] if public else item['private_storage_key']
    path=safe_path(request,key)
    if not path.is_file():err(404,'Not found')
    mime='text/plain; charset=utf-8' if public and item['safe_type']=='PDF' else MIME[item['safe_type']]
    return Response(path.read_bytes(),media_type=mime,headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Disposition':'attachment; filename="evidence"'})

@router.get('/admin/attachments')
def pending_evidence(request:Request,session=Depends(get_session)):
    if session['role']!='ADMIN':err(403,'Forbidden')
    with request.app.state.engine.connect() as c:
        rows=c.execute(select(s.attachments.c.id,s.attachments.c.purpose,s.attachments.c.safe_type,s.attachments.c.size,s.attachments.c.state,s.attachments.c.declared_faces,s.attachments.c.declared_nsfw,s.attachments.c.declared_sensitive,s.attachments.c.created_at).join(s.reports,s.reports.c.id==s.attachments.c.report_id).where(s.attachments.c.state=='PENDING_REVIEW',s.attachments.c.case_id.is_(None),s.attachments.c.public_requested.is_(True),s.reports.c.visibility=='PUBLIC',s.reports.c.issue_id.is_not(None)).order_by(s.attachments.c.created_at)).mappings().all()
    return [dict(row) for row in rows]

@router.post('/attachments/{attachment_id}/review')
def review(attachment_id:str,request:Request,faces_checked:bool=Form(...),nsfw_checked:bool=Form(...),pii_checked:bool=Form(...),restricted_checked:bool=Form(...),reason:str=Form(...),session=Depends(get_session)):
    if session['role']!='ADMIN':err(403,'Forbidden')
    with immediate_transaction(request.app.state.engine) as c:
        item=c.execute(select(s.attachments).where(s.attachments.c.id==attachment_id)).mappings().first()
        if not item:err(404,'Not found')
        report=c.execute(select(s.reports.c.visibility,s.reports.c.issue_id).where(s.reports.c.id==item['report_id'])).mappings().first() if item['report_id'] else None
        detected=c.execute(select(s.attachment_reviews.c.id).where(s.attachment_reviews.c.attachment_id==attachment_id,s.attachment_reviews.c.local_face_result=='DETECTED')).first()
        if not (not detected and faces_checked and nsfw_checked and pii_checked and restricted_checked and reason.strip() and item['public_requested'] and item['case_id'] is None and report and report['visibility']=='PUBLIC' and report['issue_id'] and item['declared_faces']!='YES' and item['declared_nsfw']!='YES' and item['declared_sensitive']!='YES'):err(403,'Review requirements not met')
        c.execute(update(s.attachments).where(s.attachments.c.id==attachment_id).values(state='PUBLIC_APPROVED',updated_at=stamp(now())))
        c.execute(insert(s.attachment_reviews).values(id=str(uuid.uuid4()),attachment_id=attachment_id,local_face_result='NOT_CONFIGURED',review_flags='manual inspection',reviewer_id=session['user_id'],safe_reason='Manual safety review',created_at=stamp(now())))
    return {'state':'PUBLIC_APPROVED','face_detection':'NOT_CONFIGURED'}

@router.post('/attachments/{attachment_id}/revoke')
def revoke(attachment_id:str,request:Request,session=Depends(get_session)):
    with immediate_transaction(request.app.state.engine) as c:
        result=c.execute(update(s.attachments).where(s.attachments.c.id==attachment_id,s.attachments.c.owner_id==session['user_id']).values(state='PRIVATE',public_requested=False,external_consent=False,updated_at=stamp(now())))
        if not result.rowcount:err(404,'Not found')
    return {'state':'PRIVATE'}
