"""Local identity, sessions and restricted synthetic demo operations."""
import csv
import hashlib
import hmac
import ipaddress
import json
import secrets
import smtplib
import shutil
import threading
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, insert, select, update, text
from app import schema as s
from app.database import immediate_transaction
from app.seed import seed_demo, uid

router = APIRouter(prefix='/api/v1')
COOKIE = 'reportfix_session'
_rate_lock = threading.Lock()
_requests = {}

def now(): return datetime.now(timezone.utc)
def stamp(value): return value.isoformat(timespec='microseconds')
def parse(value): return datetime.fromisoformat(value.replace('Z', '+00:00'))
def err(status, message): raise HTTPException(status_code=status, detail=message)
def digest(token): return hashlib.sha256(token.encode()).hexdigest()
def mac(key, value): return hmac.new(bytes.fromhex(key), value.encode(), hashlib.sha256).hexdigest()
def local_keys(request):
    return json.loads((request.app.state.config.runtime_dir / 'local-secrets.json').read_text(encoding='utf-8'))

def canonical_email(email, domains):
    email = email.strip().lower()
    allowed = {x.strip().lower() for x in domains.split(',') if x.strip()}
    if len(email) > 254 or email.count('@') != 1 or any(c.isspace() for c in email): return None
    local, domain = email.split('@')
    if not local or not domain or domain not in allowed: return None
    return email

def send_otp(settings, recipient, code):
    if not settings.smtp_host or not settings.smtp_from:
        raise RuntimeError('SMTP not configured')
    msg = EmailMessage()
    msg['From'], msg['To'], msg['Subject'] = settings.smtp_from, recipient, 'ReportFix verification code'
    msg.set_content('Your ReportFix verification code is ' + code + '. It expires in five minutes.')
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)

def create_session(conn, user_id, operator=False):
    raw = secrets.token_urlsafe(32)
    conn.execute(insert(s.sessions).values(id=str(uuid.uuid4()), token_digest=digest(raw), user_id=user_id,
        expires_at=stamp(now()+timedelta(hours=12)), demo_operator=operator, generation=0))
    return raw

def set_cookie(response, token):
    response.set_cookie(COOKIE, token, max_age=43200, httponly=True, samesite='strict', secure=False, path='/')

def get_session(request: Request):
    raw = request.cookies.get(COOKIE)
    if not raw: err(401, 'Authentication required')
    with request.app.state.engine.connect() as conn:
        row = conn.execute(select(s.sessions, s.users.c.role, s.users.c.department_id, s.users.c.confidential_capability,
            s.users.c.verified, s.users.c.demo, s.users.c.trust_cache).join(s.users, s.sessions.c.user_id == s.users.c.id)
            .where(s.sessions.c.token_digest == digest(raw))).mappings().first()
    if not row or parse(row['expires_at']) <= now(): err(401, 'Session expired or invalid')
    return dict(row)

def require_roles(*roles):
    def verify(session=Depends(get_session)):
        if session['role'] not in roles: err(403, 'Forbidden')
        return session
    return verify

def require_department(session, department):
    if session['role'] != 'ADMIN' and (session['role'] != 'STAFF' or session['department_id'] != department):
        err(403, 'Forbidden')

def require_confidential(session):
    if not session['confidential_capability']: err(403, 'Forbidden')

def is_loopback(request):
    try: return ipaddress.ip_address(request.client.host).is_loopback
    except (ValueError, AttributeError): return False

def demo_guard(request):
    config = request.app.state.config
    if not config.demo_mode or config.runtime_dir.name.lower() != 'demo' or not is_loopback(request): err(404, 'Not found')
    with request.app.state.engine.connect() as conn:
        if conn.execute(select(s.users.c.id).where(s.users.c.demo.is_(False)).limit(1)).first(): err(403, 'Demo isolation required')
        if conn.execute(select(s.verified_identities.c.token).limit(1)).first(): err(403, 'Demo isolation required')
    marker = config.runtime_dir / '.reportfix-demo'
    if not marker.is_file() or marker.is_symlink() or marker.read_text(encoding='utf-8') != 'synthetic-demo-v1': err(403, 'Demo isolation required')

def operator(request: Request, session=Depends(get_session)):
    demo_guard(request)
    if not session['demo_operator'] or not session['demo']: err(403, 'Demo operator required')
    return session

class OtpRequest(BaseModel):
    email: str = Field(max_length=254)
class OtpVerify(BaseModel):
    challenge: str = Field(max_length=36)
    code: str = Field(pattern=r'^\d{6}$')
class Switch(BaseModel):
    user: str = Field(max_length=36)
class Advance(BaseModel):
    hours: int = Field(ge=1, le=8760)
class ProviderMode(BaseModel):
    unavailable: bool

@router.post('/auth/request-otp')
def request_otp(data: OtpRequest, request: Request):
    config=request.app.state.config
    if config.demo_mode or config.runtime_dir.name.lower() == 'demo': err(403, 'Real verification is disabled in synthetic demo mode')
    if not config.smtp_host or not config.smtp_from or not config.allowed_student_email_domains: err(503, 'Email verification is not configured')
    recipient=canonical_email(data.email,config.allowed_student_email_domains)
    if not recipient: err(400, 'Email cannot be verified')
    current=now(); client=request.client.host if request.client else ''
    with _rate_lock:
        recent=[t for t in _requests.get(client,[]) if t > current-timedelta(minutes=10)]
        if len(recent)>=20: err(429, 'Please try later')
        _requests[client]=recent+[current]
    keys=local_keys(request); identity=mac(keys['identity_hmac'],recipient)
    challenge=str(uuid.uuid4()); code=f'{secrets.randbelow(1000000):06d}'
    otp_hash=mac(keys['session'],challenge+':'+code)
    with immediate_transaction(request.app.state.engine) as conn:
        conn.execute(delete(s.verification_challenges).where(s.verification_challenges.c.expires_at < stamp(current)))
        last=conn.execute(select(s.verification_challenges.c.last_sent).where(s.verification_challenges.c.token==identity).order_by(s.verification_challenges.c.last_sent.desc())).scalar()
        if last and parse(last)>current-timedelta(seconds=60): err(429,'Please try later')
        conn.execute(delete(s.verification_challenges).where(s.verification_challenges.c.token==identity))
        conn.execute(insert(s.verification_challenges).values(id=challenge,token=identity,otp_digest=otp_hash,expires_at=stamp(current+timedelta(minutes=5)),attempts=0,consumed=False,last_sent=stamp(current)))
    try: send_otp(config,recipient,code)
    except (OSError, smtplib.SMTPException, RuntimeError):
        with immediate_transaction(request.app.state.engine) as conn: conn.execute(delete(s.verification_challenges).where(s.verification_challenges.c.id==challenge))
        err(503,'Email delivery unavailable')
    return {'challenge':challenge,'message':'If eligible, a verification code has been sent.'}

@router.post('/auth/verify-otp')
def verify_otp(data: OtpVerify, request: Request, response: Response):
    if request.app.state.config.demo_mode or request.app.state.config.runtime_dir.name.lower() == 'demo': err(403,'Real verification is disabled in synthetic demo mode')
    keys=local_keys(request); current=now(); failure=False; token=None
    with immediate_transaction(request.app.state.engine) as conn:
        row=conn.execute(select(s.verification_challenges).where(s.verification_challenges.c.id==data.challenge)).mappings().first()
        if not row or row['consumed'] or parse(row['expires_at'])<=current or row['attempts']>=5:
            if row and (parse(row['expires_at'])<=current or row['attempts']>=5): conn.execute(delete(s.verification_challenges).where(s.verification_challenges.c.id==data.challenge))
            failure=True
        elif not hmac.compare_digest(row['otp_digest'],mac(keys['session'],data.challenge+':'+data.code)):
            conn.execute(update(s.verification_challenges).where(s.verification_challenges.c.id==data.challenge).values(attempts=row['attempts']+1));failure=True
        else:
            user=conn.execute(select(s.verified_identities.c.user_id).where(s.verified_identities.c.token==row['token'])).scalar()
            if not user:
                user=str(uuid.uuid4())
                conn.execute(insert(s.users).values(id=user,role='STUDENT',verified=True,demo=False,created_at=stamp(current)))
                conn.execute(insert(s.verified_identities).values(token=row['token'],user_id=user,created_at=stamp(current)))
            old=request.cookies.get(COOKIE)
            if old: conn.execute(delete(s.sessions).where(s.sessions.c.token_digest==digest(old)))
            token=create_session(conn,user)
            conn.execute(delete(s.verification_challenges).where(s.verification_challenges.c.id==data.challenge))
    if failure: err(400,'Invalid or expired verification code')
    set_cookie(response,token)
    return {'verified':True,'role':'STUDENT'}

@router.get('/auth/me')
def me(session=Depends(get_session)):
    return {'role':session['role'],'department':session['department_id'],'verified':session['verified'],
            'synthetic':session['demo'],'confidential_capability':session['confidential_capability'],
            'trust':session['trust_cache'] if session['role']=='STUDENT' else None}

@router.post('/auth/logout')
def logout(request: Request, response: Response, session=Depends(get_session)):
    with immediate_transaction(request.app.state.engine) as conn: conn.execute(delete(s.sessions).where(s.sessions.c.id==session['id']))
    response.delete_cookie(COOKIE,path='/');return {'ok':True}

@router.post('/demo/bootstrap')
def bootstrap(request: Request, response: Response, x_demo_operator_token: str = Header(default='')):
    demo_guard(request)
    path=request.app.state.config.runtime_dir / 'demo-operator.token'
    if not path.is_file() or path.is_symlink() or not hmac.compare_digest(x_demo_operator_token,path.read_text(encoding='utf-8').strip()): err(403,'Demo operator required')
    with immediate_transaction(request.app.state.engine) as conn:
        old=request.cookies.get(COOKIE)
        if old: conn.execute(delete(s.sessions).where(s.sessions.c.token_digest==digest(old)))
        token=create_session(conn,uid('user:admin'),True)
    set_cookie(response,token);return {'synthetic':True,'role':'ADMIN'}

@router.get('/demo/users')
def demo_users(request: Request, session=Depends(operator)):
    with request.app.state.engine.connect() as conn:
        rows=conn.execute(select(s.users.c.id,s.users.c.role,s.users.c.department_id,s.users.c.confidential_capability).where(s.users.c.demo.is_(True)).order_by(s.users.c.role,s.users.c.department_id,s.users.c.id)).mappings().all()
    return [{'selector':r['id'],'role':r['role'],'department':r['department_id'],'confidential_capability':r['confidential_capability'],'synthetic':True} for r in rows]

@router.post('/demo/switch-user')
def switch(data: Switch, request: Request, response: Response, session=Depends(operator)):
    with immediate_transaction(request.app.state.engine) as conn:
        user=conn.execute(select(s.users.c.id,s.users.c.role).where(s.users.c.id==data.user,s.users.c.demo.is_(True))).mappings().first()
        if not user: err(404,'Synthetic user not found')
        conn.execute(delete(s.sessions).where(s.sessions.c.id==session['id']))
        token=create_session(conn,user['id'],True)
    set_cookie(response,token);return {'role':user['role'],'synthetic':True}

@router.post('/demo/create-student')
def create_student(request: Request, session=Depends(operator)):
    user=str(uuid.uuid4())
    with immediate_transaction(request.app.state.engine) as conn:
        conn.execute(insert(s.users).values(id=user,role='STUDENT',verified=True,demo=True,created_at=stamp(now())))
    return {'selector':user,'role':'STUDENT','synthetic':True}

@router.post('/demo/advance-time')
def advance(data: Advance, request: Request, session=Depends(operator)):
    with immediate_transaction(request.app.state.engine) as conn:
        value=conn.execute(select(s.system_settings.c.value).where(s.system_settings.c.key=='demo_clock')).scalar_one()
        value=stamp(parse(value)+timedelta(hours=data.hours))
        conn.execute(update(s.system_settings).where(s.system_settings.c.key=='demo_clock').values(value=value))
    return {'demo_time':value}

@router.post('/demo/provider-mode')
def provider_mode(data: ProviderMode, request: Request, session=Depends(operator)):
    with immediate_transaction(request.app.state.engine) as conn:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        stmt=sqlite_insert(s.system_settings).values(key='provider_unavailable',value='true' if data.unavailable else 'false')
        conn.execute(stmt.on_conflict_do_update(index_elements=['key'],set_={'value':stmt.excluded.value}))
    return {'unavailable':data.unavailable}

@router.post('/demo/reset')
def reset(request: Request, response: Response, session=Depends(operator)):
    root=request.app.state.config.runtime_dir
    uploads=root / 'uploads'
    quarantine=None
    if uploads.exists() or uploads.is_symlink():
        if uploads.is_symlink() or not uploads.is_dir() or uploads.resolve().parent != root.resolve():
            err(409,'Unsafe demo upload directory')
        quarantine=root / ('.reset-uploads-'+uuid.uuid4().hex)
        uploads.rename(quarantine)
    try:
        with immediate_transaction(request.app.state.engine) as conn:
            conn.execute(text('DROP TRIGGER IF EXISTS trust_events_no_delete'))
            for table in reversed(s.metadata.sorted_tables): conn.execute(delete(table))
            conn.execute(text("CREATE TRIGGER trust_events_no_delete BEFORE DELETE ON trust_events BEGIN SELECT RAISE(ABORT, 'trust events are immutable'); END"))
            seed_demo(request.app.state.engine,conn)
            token=create_session(conn,uid('user:admin'),True)
    except BaseException:
        if quarantine is not None: quarantine.rename(uploads)
        raise
    if quarantine is not None: shutil.rmtree(quarantine)
    set_cookie(response,token)
    return {'reset':True,'synthetic':True}
