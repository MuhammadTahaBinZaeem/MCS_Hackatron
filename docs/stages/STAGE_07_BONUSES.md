# Stage 07 — Trending, moderation, summaries and metrics

## Prerequisites
Stage 06 PASS and explicit user authorization; verify evidence in PROGRESS.md.

## Required contracts
Read root AGENTS.md, README_SPEC.md, PROBLEM_STATEMENT.md, FINAL_DECISIONS.md, REQUIREMENTS.md and PROGRESS.md plus: RULES.md, AI.md, SECURITY.md, API.md.

## Authorized scope and deliverables
Implement all bonus features: weighted recent unique participation trend excluding closed/private; spam rate limits and emergency exception; temporal new-account vote clusters and corroborated suspicious clusters; admin review and audit, verified invalidation/recalculation, no auto penalties from suspicion. Calculate stats from SQL, sanitized aggregate AI summary with deterministic labeled fallback; actual processing metrics. Add endpoints to demo and admin workflows.

## Acceptance / stopping gate
Trend 24/48h boundaries, unique counts and privacy; rate limit ordinary floods, emergency retained; cluster flags detectable without false automatic penalties; adjudication evidence required; summary numbers consistent with aggregate; provider-off fallback labeled; no confidential text/IDs in summary input/output.

Run targeted tests and the full existing suite, review diff, update docs/PROGRESS.md with real results and known limitations. Do not mark PASS if mandatory gate fails. No implementation of later stages. Do not push or commit without authorization.

**STOP — Awaiting explicit authorization for Stage 08.**
