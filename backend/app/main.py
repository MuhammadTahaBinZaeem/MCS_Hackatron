from contextlib import asynccontextmanager
import os
import secrets
import anyio
from sqlalchemy import inspect, select

from fastapi import FastAPI, Response
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.database import create_database, database_ready
from app.secrets_store import ensure_local_secrets
from app.registry import router as registry_router
from app.reports_api import router as reports_router
from app.issues import router as issues_router
from app.community import router as community_router
from app.attachments import router as attachment_router
from app.dashboard import router as dashboard_router
from app.azure_provider import AzureTextProvider
from app.identity import router as identity_router
from app import schema
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi.exceptions import RequestValidationError


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        ensure_local_secrets(config.runtime_dir)
        application.state.engine = create_database(config.runtime_dir)
        application.state.config = config
        application.state.text_provider = AzureTextProvider(config)
        application.state.request_lock = anyio.Lock()
        if config.demo_mode and config.runtime_dir.name.lower() == 'demo' and inspect(application.state.engine).has_table('users'):
            with application.state.engine.connect() as conn:
                real_user=conn.execute(select(schema.users.c.id).where(schema.users.c.demo.is_(False)).limit(1)).first()
                real_identity=conn.execute(select(schema.verified_identities.c.token).limit(1)).first()
            if not real_user and not real_identity:
                marker=config.runtime_dir / '.reportfix-demo'
                token_file=config.runtime_dir / 'demo-operator.token'
                if marker.is_symlink() or token_file.is_symlink(): raise RuntimeError('Invalid demo capability path')
                for path, content in [(marker,'synthetic-demo-v1'),(token_file,secrets.token_urlsafe(32))]:
                    try:
                        fd=os.open(path,os.O_WRONLY | os.O_CREAT | os.O_EXCL,0o600)
                        with os.fdopen(fd,'w',encoding='utf-8') as handle: handle.write(content)
                    except FileExistsError: pass
        try:
            yield
        finally:
            application.state.engine.dispose()

    application = FastAPI(title="ReportFix", lifespan=lifespan)
    application.include_router(registry_router)
    application.include_router(identity_router)
    application.include_router(reports_router)
    application.include_router(issues_router)
    application.include_router(community_router)
    application.include_router(attachment_router)
    application.include_router(dashboard_router)

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request, _exc):
        return JSONResponse(status_code=422, content={'detail':'Invalid request'})

    @application.middleware('http')
    async def origin_and_serialization(request, call_next):
        if request.method not in ('GET','HEAD','OPTIONS'):
            expected=f'http://127.0.0.1:{config.port}'
            if request.headers.get('origin') != expected:
                return JSONResponse(status_code=403,content={'detail':'Invalid origin'})
        async with application.state.request_lock:
            return await call_next(request)

    @application.get("/api/v1/healthz")
    def health():
        return {"status": "ok"}

    @application.get("/api/v1/readyz")
    def ready(response: Response):
        try:
            if database_ready(application.state.engine):
                return {"status": "ready"}
        except (SQLAlchemyError, OSError):
            pass
        response.status_code = 503
        return {"status": "not_ready"}

    @application.get('/{asset_path:path}',include_in_schema=False)
    def frontend(asset_path:str):
        if asset_path.startswith('api/') or asset_path=='api':return JSONResponse(status_code=404,content={'detail':'Not found'})
        web_root=Path(__file__).resolve().parents[2]/'web'
        built=(web_root/'dist').resolve()
        root=built if (built/'index.html').is_file() else (web_root/'static').resolve()
        candidate=(root/asset_path).resolve()
        if not candidate.is_relative_to(root):return JSONResponse(status_code=404,content={'detail':'Not found'})
        if candidate.is_file():return FileResponse(candidate)
        index=root/'index.html'
        if index.is_file():return FileResponse(index)
        return JSONResponse(status_code=503,content={'detail':'Frontend build not found'})

    return application


app = create_app()
