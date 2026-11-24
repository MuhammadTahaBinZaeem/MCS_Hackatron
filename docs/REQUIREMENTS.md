# Requirements and acceptance traceability

Organizer requirements R1–R9 are authoritative; team extensions E1–E8 and bonus B1–B3 are also build targets. See PROBLEM_STATEMENT.md for exact source wording.

| ID | Required behavior / acceptance | Stage |
|---|---|---|
| R1 | Other accepts plain English/Roman Urdu/mixed text/typos with no prefilled selection; returns department, validated location, priority, one-line reason or clarification | 3–4 |
| R2 | Same issue at same location across languages groups into a single canonical issue with unique affected count; WiFi vs AC, distinct rooms/assets remain separate | 4 |
| R3 | Actual fire/sparks/gas/medical emergency gets 100 regardless of tone; urgent/caps alone no increase | 3–4 |
| R4 | Injection cannot change rules, permissions or priority; valid complaint alongside attack remains processable | 3,9 |
| R5 | Harassment/ragging private even when public selected; no public board, unrelated staff, reporter identity or external provider disclosure | 2–3,6 |
| R6 | Unknown/ambiguous location prompts clarification; no fabricated route or changed room numbers | 3 |
| R7 | Staff claim resolved triggers affected-only verification; enough credible disputes reopen; next round distinct | 5 |
| R8 | Trust influences votes/reports; independent verified outcomes adjust bounded ledger; explain own score | 5 |
| R9 | Unique credible crowd raises priority; one high-trust student cannot dominate; safety override | 4–5 |
| J1 | Switch among all synthetic users with one click and no passwords | 2,10 |
| J2 | Instantly create new simulated student | 2,10 |
| J3 | Reset all demo data including attachments, sessions, flags and time | 2,6,9,10 |
| B1 | Trending board from weighted recent unique participation | 7 |
| B2 | AI-written admin summary from sanitized validated aggregates; honest non-AI fallback | 7 |
| B3 | Spam/brigading rules detect clusters and repeated abuse, audit moderation | 7 |
| E1 | One verified account per canonical email, OTP expiry, no raw email persistence after challenge, private ownership | 2 |
| E2 | Anonymous dashboard with General and six department filters, search, category/status/priority/sort | 4,10 |
| E3 | 2nd/Disagree no self-vote or double count; changes atomic; distinct resolution voting | 5 |
| E4 | File/image as report or supporting evidence, private consent, face-first declaration, safe validation/retrieval | 6 |
| E5 | Optional vision classification adapter with manual fallback; no unreviewed external image uploads | 8 |
| E6 | Provider failure and offline mode; no data loss; structured classifications and measured AI usage | 3,7–9 |
| E7 | Polished template-based responsive frontend, actual API, no mocks, role views and easy judge access | 10 |
| E8 | Repeatable loopback start, SQLite persistence, isolated tests, local reset, no hosting | 0–10 |

## Acceptance priorities
40 marks live attack, 20 core, 20 community, 10 approach, 10 pitch, up to 10 bonus. Visual design not scored. All requirements are intended targets. No stage or bonus is marked complete without evidence. The organizer requires every team member to speak in the two-minute pitch even if one developer/Codex implemented the system.
