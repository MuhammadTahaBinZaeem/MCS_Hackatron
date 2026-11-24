# Stage 06 — Private uploads and evidence handling

## Prerequisites
Stage 05 PASS and explicit user authorization; verify evidence in PROGRESS.md.

## Required contracts
Read root AGENTS.md, README_SPEC.md, PROBLEM_STATEMENT.md, FINAL_DECISIONS.md, REQUIREMENTS.md and PROGRESS.md plus: SECURITY.md, AI.md, DESIGN.md, DATA_MODEL.md, API.md.

## Authorized scope and deliverables
Implement staged owner-bound multipart uploads, allowlist/stream limits/signature/decoder checks, random filenames, private storage, image metadata stripping and sanitized derivative, PDF/TXT extraction limits, face-first declaration then NSFW/sensitive/public and external consent, local face detector via verified YuNet/OpenCV where available, review state machine and manual checklist, private retrieval authorization, sanitized public derivative only. Link to main complaint or evidence; file-only manual classification when no vision. Reject prohibited files, clean orphans, reset demo uploads, compensate write failures. Integrate extracted text as untrusted and screen before external use.

## Acceptance / stopping gate
Valid JPG/PNG/WebP/PDF/TXT accepted, invalid types/size/traversal/corrupt rejected; staged cross-user references denied; face yes/detected, NSFW, uncertainty and confidential never public; review unavailable fails closed; consent required and revocation enforced; private file guessed ID denied; image-only manual path, safe PDF handling and reset cleanup; actual detector test or explicit unconfigured review-only fallback.

Run targeted tests and the full existing suite, review diff, update docs/PROGRESS.md with real results and known limitations. Do not mark PASS if mandatory gate fails. No implementation of later stages. Do not push or commit without authorization.

**STOP — Awaiting explicit authorization for Stage 07.**
