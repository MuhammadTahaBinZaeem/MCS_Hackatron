# Stage 00 — Foundation and interfaces

## Prerequisites
None; inspect actual repository.

## Required contracts
Read root AGENTS.md, README_SPEC.md, PROBLEM_STATEMENT.md, FINAL_DECISIONS.md, REQUIREMENTS.md and PROGRESS.md plus: ARCHITECTURE.md, LOCAL_RUN.md, DEPENDENCIES.md, SECURITY.md.

## Authorized scope and deliverables
Inspect repository, existing tools and clean/dirty state. Set up Python 3.12/uv project, pinned dependencies, app skeleton, settings, .gitignore, .env.example, SQLite connection, migrations scaffold, loopback health/readiness, local scripts and test fixtures. Create typed text/vision/storage/email interfaces, disabled providers returning explicit unavailable, injectable clock. Generate local secrets safely. Do not implement schema beyond migration scaffolding or import frontend.

## Acceptance / stopping gate
Health and readiness on loopback; config fails safely for invalid paths/secrets; SQLite foreign keys/WAL configured; pytest runs; disabled provider reports NOT_CONFIGURED; no external dependencies at runtime for startup; no tracked secret/runtime files.

Run targeted tests and the full existing suite, review diff, update docs/PROGRESS.md with real results and known limitations. Do not mark PASS if mandatory gate fails. No implementation of later stages. Do not push or commit without authorization.

**STOP — Awaiting explicit authorization for Stage 01.**
