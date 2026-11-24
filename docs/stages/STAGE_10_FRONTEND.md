# Stage 10 — Final UI import, API integration and demo

## Prerequisites
Stage 09 PASS and explicit user authorization; verify evidence in PROGRESS.md.

## Required contracts
Read root AGENTS.md, README_SPEC.md, PROBLEM_STATEMENT.md, FINAL_DECISIONS.md, REQUIREMENTS.md and PROGRESS.md plus: DESIGN.md, DEPENDENCIES.md, API.md, TESTING.md, LOCAL_RUN.md.

## Authorized scope and deliverables
Only now import Shadcn Admin from pinned reviewed revision with license notices, remove sample data and unrelated demo screens, use existing components/layout. Connect actual API to all screens: community filters, single guided/Other report, evidence/privacy, personal history/trust, department queue, admin/moderation/summary/trending, confidential inbox, demo controls. Clear cache on switch/logout/reset; safe escaped content and errors; same-origin compiled assets, local loopback start. Run Playwright and full backend regression. Prepare local demo runbook and two-minute pitch with three speakers; no deployment or extra decorative design.

## Acceptance / stopping gate
Build and browser tests pass; full actual API workflow through UI including duplicate, privacy, trust, resolution and reset; no mocked screens; role/cache tests, evidence review, responsive light/dark, provider failure and error states; final traceability and actual test counts, launch instructions. Stop and await demo review, no publishing.

Run targeted tests and the full existing suite, review diff, update docs/PROGRESS.md with real results and known limitations. Do not mark PASS if mandatory gate fails. No implementation of later stages. Do not push or commit without authorization.

**STOP — Final stage complete or blocked; awaiting demo review.**
