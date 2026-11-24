# Local execution only

## Stage 00 verified setup

From the repository root with Python 3.12 and `uv` installed:

```powershell
uv sync --locked
uv run alembic upgrade head
$env:PYTHONPATH = 'backend'
uv run python -m app.seed --demo
uv run python -m app
```

In another terminal, run `uv run pytest -q` and visit `http://127.0.0.1:8000/api/v1/healthz` or `/api/v1/readyz`. `uv sync --locked` uses the lockfile; do not copy `security/api.env` into `.env` or expose credentials. On POSIX shells, use `export PYTHONPATH=backend`. The domain migration and demo seed are implemented, while user workflows are not yet implemented. On first startup the app creates local secrets in the ignored runtime directory and restricts its directory to the current user; do not share this directory. The local environment must permit `whoami` and `icacls` on Windows.

Stage 03 adds complaint preview, pending submissions, clarification and confidential case handling; public issue creation is deferred. The Azure adapter is disabled by default. To enable it in PowerShell from the project root, without displaying credentials:

```powershell
$env:AZURE_ENABLED = 'true'
$env:AZURE_CREDENTIAL_FILE = 'security/api.env'
$env:PYTHONPATH = 'backend'
uv run python -m app
```

The ignored credential file must contain `endpoint` and `key`; never copy credentials into tracked files. Azure receives locally derived safe concepts only; sensitive or uncertain text is never sent. Unrecognized words alone do not restrict an ordinary report. Local matching remains available offline. Real OTP requires `DEMO_MODE=false`, a separate runtime directory whose name is not `demo`, an approved `ALLOWED_STUDENT_EMAIL_DOMAINS` list, and configured SMTP with STARTTLS. No real identities are permitted in demo mode.

For local synthetic judge controls, first start the seeded app in demo mode, then bootstrap an operator session from the local capability file (do not share it):

```powershell
$capability = (Get-Content -Raw runtime/demo/demo-operator.token).Trim()
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/demo/bootstrap -WebSession $session -Headers @{Origin='http://127.0.0.1:8000'; 'X-Demo-Operator-Token'=$capability}
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/demo/users -WebSession $session
```

Mutating API requests require the matching loopback `Origin` header and the operator session cookie. Demo reset operates only in the dedicated `demo` runtime; it removes demo uploads and reseeds the database. Stage 06 must integrate its storage lifecycle with this reset path. The provider failure switch disables Azure calls during the demo.

Attachment screening has an optional local OpenCV YuNet adapter. Set `FACE_MODEL_PATH` to a locally installed, appropriately licensed YuNet model and install compatible `opencv-python` and `numpy` to enable it. Those optional components are not installed or verified by this project. Without them, screening reports `NOT_CONFIGURED` and requires human review; unreviewed images are never sent to Featherless.

No deployment tasks. Target Linux/Windows/macOS with Python 3.12, uv, Git and Node LTS/pnpm for Stage 10. Keep instructions compatible with existing environment; check installed versions. Stage 0 implements working local scripts and documents actual commands; examples below are intended contracts, not executed commands yet.

```sh
uv sync
uv run alembic upgrade head
uv run python -m app.seed --demo
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
uv run pytest
```
Run from configured project root or use explicit app directory/module paths; make scripts handle working directory reliably. `/docs` for Swagger, `/api/v1/healthz` and `/api/v1/readyz`. At Stage 10 build the imported frontend (`pnpm install --frozen-lockfile`, `pnpm build` as applicable); serve dist through FastAPI, `/api/v1` not caught by SPA fallback. Document one start command and demo reset. Do not bind to 0.0.0.0. No CDN or network requirement after dependencies installed except optional SMTP/AI.

## Configuration (.env.example; never actual secrets)
```dotenv
APP_ENV=local
DEMO_MODE=true
RUNTIME_DIR=./runtime/demo
HOST=127.0.0.1
PORT=8000
DATABASE_URL=sqlite:///./runtime/demo/reportfix.db
SESSION_SECRET=
IDENTITY_HMAC_SECRET=
ALLOWED_STUDENT_EMAIL_DOMAINS=
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=
AZURE_MODEL_FAST=gpt-5.4-nano
AZURE_MODEL_STANDARD=gpt-5.4-mini
AZURE_MODEL_ADVANCED=gpt-5.4
AZURE_MODEL_ESCALATION=gpt-5.6-luna
FEATHERLESS_BASE_URL=
FEATHERLESS_API_KEY=
FEATHERLESS_TEXT_MODEL=
FEATHERLESS_VISION_MODEL=
VISION_ENABLED=false
RESOLUTION_WINDOW_HOURS=48
MAX_UPLOAD_MB=10
MAX_ATTACHMENTS=5
MAX_REPORT_UPLOAD_MB=25
```
Use persistent local generated secrets (ignored file, restricted permissions), not constant defaults. Demo accounts are synthetic; real mode separate runtime and no switch/reset. `.gitignore` includes `.env`, runtime/, database/WAL/SHM, uploads, logs, caches, node_modules and dist. Keep seed fixtures synthetic and sanitized. Test fresh start, restart and reset; backup only demo fixture/state when useful, no arbitrary file deletion. Record provider capability probe with no secrets; actual API requests only with user-provided keys. Offline fallback must work without keys. Never commit credentials or actual complaint data to the public repository.
