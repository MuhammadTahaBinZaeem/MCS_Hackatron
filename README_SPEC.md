# ReportFix | Local-only implementation specification v1.1

Target repository: https://github.com/MuhammadTahaBinZaeem/MCS_Hackatron (default branch: main). This is a specification pack, not implemented software. Extract into repository root, preserving directories. Do not publish the organizer's problem statement unless permitted; the repository is public. Keep actual complaints, credentials, attachments, SQLite files and local logs out of Git.

## Read in this order

1. `docs/PROBLEM_STATEMENT.md` — organizer's original requirements (Markdown transcription).
2. `AGENTS.md` — mandatory coding-agent behavior and stop protocol.
3. `docs/FINAL_DECISIONS.md` — locked product choices and scope.
4. `docs/REQUIREMENTS.md` — traceable requirements and acceptance criteria.
5. `docs/DESIGN.md` — user flows and screen designs (implement UI last).
6. `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/API.md` — implementation contracts.
7. `docs/RULES.md`, `docs/SECURITY.md`, `docs/AI.md` — authoritative logic and safety details.
8. `docs/DEPENDENCIES.md`, `docs/TESTING.md`, `docs/LOCAL_RUN.md` — reusable code, quality and execution.
9. `docs/STAGES.md` — stage index; `docs/stages/` — individual implementation checklists.
10. `docs/PROGRESS.md` — actual execution status, initially NOT STARTED.
11. `prompts/00_CONTEXT.md` — give to GPT/Codex before any implementation. `prompts/01_STAGE_00.md` through `prompts/11_STAGE_10.md` — issue one at a time, only after reviewing previous output.

## Authority and conflict resolution

Organizer requirements take precedence over team preferences. FINAL_DECISIONS controls team choices; detailed RULES, SECURITY, AI, DATA_MODEL and API define how to implement them. Requirements are acceptance targets, not claims of completed work. Stop and report a conflict before changing any locked policy. New changes must be recorded in FINAL_DECISIONS and affected contracts before implementation.

## Scope

Local laptop only. No Render, hosted database, object-storage service, Docker, or cloud deployment. Internet is optional for AI, SMTP and acquiring dependencies; local workflows must survive provider outages. Target a fast demo-ready MVP, not a production identity/privacy certification. Aim for ~60 minutes of coding as an aggressive budget, then use remaining 2.5-hour event time for quality and testing. Never sacrifice required controls to hit a timer.
