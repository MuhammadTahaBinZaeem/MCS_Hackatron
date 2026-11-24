# Verification strategy and attack test matrix

Tests run locally, isolated temporary DB/storage, injectable clock and provider stubs for deterministic testing. Stubs never equal live verification. Use parametrized tests and Hypothesis for invariants. Every stage adds targeted tests and runs full previous suite. Document command, pass/fail/skip counts in PROGRESS.md. Never hide failures. Target roughly 220 scenarios only as aspiration, not required count or guarantee; depth over breadth.

| Area | Representative checks |
|---|---|
| R1/R6 | English/Roman Urdu mixed text, typos, no selected fields, unknown Lab 99, ambiguous Lab 3, explicit numbers, contradictory selection, no routing until clarified |
| R2 | WiFi vs net same place, Lab 3 AC separate, Lab 4 separate, PC 5 vs PC 8, vague asset, closed recurrence, parallel duplicate submissions, same user repeats |
| R3/R4 | calm sparks/gas/fire/medical, urgent slow WiFi, negated hazard, quoted commands, injection mixed with valid complaint, injected document, model proposes invalid enum/priority |
| R5 | disguised harassment/ragging, conflicting public toggle, confidential direct-ID read, list/search/trending/admin summary, reclassification, logs, staff other department |
| Identity | invalid domain/OTP, expired/reused OTP, resend/attempt limits, concurrent same email, login same ID, no raw email in database/logs, demo cannot touch real mode |
| Voting | duplicate/self votes, vote change, simultaneous submission/vote, unverified/staff ineligible, disagree not affected, late joins, frozen weight, exact threshold, single dispute, 48h expiry, zero votes, all confirm, second resolution round |
| Trust | idempotent independent evidence, no majority reward, clamping, no double join/report reward, correct dispute, false report penalties, reversal, identity not revealed |
| Attachments | MIME/signature mismatch, too big, corrupt, decompression bomb, traversal, spoofed face declaration, NSFW/unknown, pending scan, consent revoked, confidential, guessed ID, cross-user association, public PDF unsafe, orphan/reset cleanup |
| Bonuses | trend time boundaries, no confidential/closed, spam rate limits and emergency exception, new account clusters, flags without automatic penalty, summary aggregate truth and failure label |
| AI | timeout, malformed/extra fields, hallucinated location, fallback, privacy gate prevents outbound, external image consent, vision unavailable, image-only manual fallback |
| Local | clean setup/migration, restart persistence, concurrent DB busy, stale version, reset isolation, old session invalidated, health/readiness, no secret files in Git |
| UI | actual report->queue->resolved->dispute->reopen, filters, anonymous profile, privacy questions, role switch/cache clear, file upload/download denial, demo reset, mobile/desktop, no mocked screens |

## Property invariants
Trust within 0..100; weights 0.5..1.5; safety always 100, ordinary <=89; unique affected count independent of duplicate attempts; vote uniqueness; no unauthenticated access; no confidential public DTOs; no unapproved public evidence; no outbound confidential bytes; no repeated reward; at most one open resolution round; rejected transitions atomic; reset deterministic. Test API authorization directly, not just UI hidden buttons.

## Demo acceptance script
Reset synthetic data. Create student; Other report Roman Urdu for Lab 3 network; another student submits paraphrase; different category stays separate. Attempt unknown room, injection, calm hazard, confidential conduct. Verify priority and privacy. Switch staff, resolve network issue; switch eligible reporters and dispute; confirm reopening. Admin adjudicates independent evidence and shows trust explanation. Demonstrate attachment face block, public safe evidence review, private ownership, trending, spam/brigading flags, AI summary and actual provider stats. Simulate outage and expiry. Reset, verify clean local data. Two-minute pitch: all 3 members speak, explain hybrid intelligence, privacy/verification and attack resilience. Use fictional examples only.
