# AGENTS.md — ReportFix implementation contract

## Required reading
Read README_SPEC.md, docs/PROBLEM_STATEMENT.md, docs/FINAL_DECISIONS.md, docs/REQUIREMENTS.md, docs/STAGES.md, docs/PROGRESS.md and the relevant contracts plus the requested stage file. Inspect actual repository state and git diff before editing. Preserve existing unrelated work. Never assume prior implementation based on documentation.

## Non-negotiable rules
- Implement only the stage explicitly authorized by the user. No preview work on a later stage; reserve only interfaces/schema explicitly required by the current stage. No frontend code or template import until Stage 10.
- Local-only: FastAPI, SQLite, local private filesystem, loopback bind. No Render, PostgreSQL, S3, Docker or hosting pipeline.
- Use mature packages and existing UI template, pin resolved versions and upstream commit/license; no redundant homemade frameworks. Keep license notices. Do not install or import questionable/unlicensed code. Do not edit unrelated files.
- Treat reports, filenames, attachment text and AI output as untrusted data. AI suggests classifications only; backend enforces location, privacy, priority, permissions, lifecycle and reputation. Never send restricted or potentially sensitive content externally.
- Default-deny authorization, private attachments until verified, no identifying data in public/admin DTOs, no raw account tokens/vote identities in responses or logs. No real student data in fixtures. Do not claim absolute anonymity.
- Test against fresh adversarial inputs; no hardcoding judge sentences, fake test successes, disabled assertions or silent fallback masquerading as live AI. Never commit secrets, local database, uploads, verification data or logs.
- Use transactional writes and database constraints. Separate tests from real/demo state. Demo switch/reset limited to loopback synthetic mode. Real email flow requires approved SMTP/domain; explicitly label simulated accounts.

## Mandatory stop protocol (every stage)
1. Inspect prerequisites, docs and prior stage test evidence. If a prerequisite is blocked, report BLOCKED and stop; do not skip ahead.
2. Implement only the requested deliverables; run targeted tests and full existing regression suite. Record exact commands, actual counts, failures and skipped external checks. Verify no sensitive/irrelevant artifacts in git diff.
3. Update docs/PROGRESS.md with stage status PASS / BLOCKED / PARTIAL, commands/results, changed files, remaining defects, dependencies and next required stage. PASS only if all required gates pass; mocks are test fixtures only, optional live integrations explicitly marked unverified.
4. Output a concise report: stage, changes, acceptance gate outcomes, commands/results, known limits, next stage name. End with `STOP — Awaiting explicit authorization for Stage NN.` Do not implement that next stage or run another agent on it. If final stage, stop and await demo review.
5. Do not push, merge, publish, or commit unless user explicitly instructs; never force push. A stage-level commit may be suggested after review.
