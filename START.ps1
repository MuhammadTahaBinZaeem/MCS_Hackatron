$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
uv sync --locked
uv run alembic upgrade head
$env:PYTHONPATH = 'backend'
$env:DEMO_MODE = 'true'
$env:RUNTIME_DIR = './runtime/demo'
if (Test-Path -LiteralPath 'security/api.env') { $env:AZURE_ENABLED = 'true' }
uv run python -m app.seed --demo
if (Test-Path -LiteralPath 'web/node_modules') {
    Push-Location 'web'
    try { npm run build } finally { Pop-Location }
} else { Write-Host 'Using the bundled local demo interface (no npm install required).' }
uv run python -m app.launcher
