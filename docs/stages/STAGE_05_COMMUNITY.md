# Stage 05 — Voting, resolution and trust

## Prerequisites
Stage 04 PASS and explicit user authorization; verify evidence in PROGRESS.md.

## Required contracts
Read root AGENTS.md, README_SPEC.md, PROBLEM_STATEMENT.md, FINAL_DECISIONS.md, REQUIREMENTS.md and PROGRESS.md plus: RULES.md, SECURITY.md, API.md, DATA_MODEL.md.

## Authorized scope and deliverables
Implement active 2ND/DISAGREE with self-vote and verified-role restrictions, atomic change and reporter participation; staff transitions, history, resolution rounds, frozen eligibility and weight, 48h deadline, threshold reopening/closure/review, repeat round separation; independent admin adjudication and idempotent trust ledger with deltas, own explanation, crowd updates. Confidential private follow-up, not public voting. Test simulated clock and races.

## Acceptance / stopping gate
Two credible disputes reopen at exact thresholds, insufficient remains pending; sole dispute review; no affected/zero confirmations -> review at expiry; all confirm closes; unauthorized/late/duplicate/self active votes rejected; reporter can verify fix; weights freeze, trust bounded and no duplicate rewards/majority penalties; staff own queue only; concurrency consistent.

Run targeted tests and the full existing suite, review diff, update docs/PROGRESS.md with real results and known limitations. Do not mark PASS if mandatory gate fails. No implementation of later stages. Do not push or commit without authorization.

**STOP — Awaiting explicit authorization for Stage 06.**
