# Stage 09 — Full backend acceptance and local startup

## Prerequisites
Stage 08 PASS and explicit user authorization; verify evidence in PROGRESS.md.

## Required contracts
Read root AGENTS.md, README_SPEC.md, PROBLEM_STATEMENT.md, FINAL_DECISIONS.md, REQUIREMENTS.md and PROGRESS.md plus: TESTING.md, REQUIREMENTS.md, API.md, LOCAL_RUN.md, SECURITY.md.

## Authorized scope and deliverables
Run full unit/integration/adversarial suites, property tests and complete Swagger/API demo. Fix backend failures within scope, verify migration/start/restart/reset, provider outage, upload limits, privacy, concurrency, exact scoring requirements and all bonus features. Freeze API DTO/OpenAPI and document current local start commands; ensure no Render/cloud infrastructure. Audit git diff and secrets. No frontend code/import. Prepare verified backend acceptance report with traceability R1–R9/J1–J3/B1–B3/E1–E8 (UI-only requirements pending Stage 10).

## Acceptance / stopping gate
All required backend tests pass, health and persistence verified, full report-to-reopen demo works, unauthorized access blocked, real failures honest, optional live checks clearly marked; no frontend yet; API schema available and local setup reproducible. If required gate fails stop BLOCKED/PARTIAL.

Run targeted tests and the full existing suite, review diff, update docs/PROGRESS.md with real results and known limitations. Do not mark PASS if mandatory gate fails. No implementation of later stages. Do not push or commit without authorization.

**STOP — Awaiting explicit authorization for Stage 10.**
