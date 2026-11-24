# Stage 02 — Anonymous verification, permissions and judge controls

## Prerequisites
Stage 01 PASS and explicit user authorization; verify evidence in PROGRESS.md.

## Required contracts
Read root AGENTS.md, README_SPEC.md, PROBLEM_STATEMENT.md, FINAL_DECISIONS.md, REQUIREMENTS.md and PROGRESS.md plus: SECURITY.md, DATA_MODEL.md, API.md.

## Authorized scope and deliverables
Implement real configurable email OTP path using approved domain and SMTP adapter, keyed digest/expiry/rate limits, canonical HMAC uniqueness token, atomic consume/login, no raw email retained; hashed session tokens and cookie/CSRF/origin controls; role dependencies, safe DTOs and confidential capability; demo-only synthetic user list/switch/create/reset/clock/provider-mode endpoints. Preserve isolated runtime; reset storage hook for Stage 06. Do not expose real identities or use synthetic OTP as real verification.

## Acceptance / stopping gate
OTP invalid/expired/replay and concurrent duplicate identity rejected; same identity login same account; unauthorized/other-dept access fails; no raw email/token exposure; demo switch rotates session, reset reseeds and invalidates old session; demo disabled outside synthetic loopback mode; live SMTP explicitly report tested or not configured.

Run targeted tests and the full existing suite, review diff, update docs/PROGRESS.md with real results and known limitations. Do not mark PASS if mandatory gate fails. No implementation of later stages. Do not push or commit without authorization.

**STOP — Awaiting explicit authorization for Stage 03.**
