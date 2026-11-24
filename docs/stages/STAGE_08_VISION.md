# Stage 08 — Late vision adapter and manual fallback

## Prerequisites
Stage 07 PASS and explicit user authorization; verify evidence in PROGRESS.md.

## Required contracts
Read root AGENTS.md, README_SPEC.md, PROBLEM_STATEMENT.md, FINAL_DECISIONS.md, REQUIREMENTS.md and PROGRESS.md plus: AI.md, SECURITY.md, DEPENDENCIES.md, API.md.

## Authorized scope and deliverables
Implement Featherless OpenAI-compatible image provider using configured exact model ID/endpoint, optionally Azure vision adapter. Validate supported capability with synthetic image only if keys supplied; typed structured outputs, timeout, privacy gate (reviewed non-sensitive no faces, explicit external consent), image suggestions -> ordinary classification validation. No vision authority over publication or location. Preserve disabled/manual path. Do not import frontend.

## Acceptance / stopping gate
Test stub validates request/response/error handling; no outbound calls for faces/NSFW/confidential/unreviewed/no consent; hallucinated location not accepted; malformed response handled; image-only complaint can be processed manually offline; report actual live capability probe or NOT CONFIGURED. Never claim live model working unless verified.

Run targeted tests and the full existing suite, review diff, update docs/PROGRESS.md with real results and known limitations. Do not mark PASS if mandatory gate fails. No implementation of later stages. Do not push or commit without authorization.

**STOP — Awaiting explicit authorization for Stage 09.**
