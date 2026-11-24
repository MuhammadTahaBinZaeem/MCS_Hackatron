# Stage 01 — Schema, registry and synthetic fixtures

## Prerequisites
Stage 00 PASS and explicit user authorization; verify evidence in PROGRESS.md.

## Required contracts
Read root AGENTS.md, README_SPEC.md, PROBLEM_STATEMENT.md, FINAL_DECISIONS.md, REQUIREMENTS.md and PROGRESS.md plus: DATA_MODEL.md, RULES.md, LOCAL_RUN.md.

## Authorized scope and deliverables
Implement all required tables/enums/constraints via Alembic, SQLite transactional helpers, separate demo/test runtime, hierarchical registry/taxonomy with Other, aliases, synthetic accounts and deterministic fixtures. Seed data must not include real names or claim actual MCS rooms. Expose read-only registry endpoints with safe DTOs; defer auth-protected exposure until Stage 02. Use seeded placeholders only where later logic not yet implemented.

## Acceptance / stopping gate
Fresh migration and seed work, re-seed idempotent; FK and unique constraints reject duplicate identity/votes/participation/event keys; active fingerprint/open round uniqueness; stable fixture state and isolated tests; database persists on restart.

Run targeted tests and the full existing suite, review diff, update docs/PROGRESS.md with real results and known limitations. Do not mark PASS if mandatory gate fails. No implementation of later stages. Do not push or commit without authorization.

**STOP — Awaiting explicit authorization for Stage 02.**
