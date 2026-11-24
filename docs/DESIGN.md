# Product and UI design

Implement no frontend until Stage 10. Before then use FastAPI Swagger and tests. Import Shadcn Admin; retain its responsive sidebar, tables, dialogs, typography, light/dark theme and accessible controls. No custom decorative animation or new design system. Use real API data only.

## Single submission flow
1. Select category -> subtype -> specific problem, or Other at any level. Top-level Other reveals free text and permits no department/location/category selections. Attachment-only reports may provide manual location and category if vision disabled.
2. Select department/location from registered options; include unknown location and Other. Additional detail is optional when structured fields describe the issue; otherwise require text or attachment.
3. Optional files: purpose MAIN_COMPLAINT or SUPPORTING_EVIDENCE. For each, ask faces first (yes/no/unsure), then NSFW/graphic, then identifying/restricted information, then explicit public consent if eligible. Default private. Show external-analysis consent separately; never assume consent from public sharing. Explain blocked visibility.
4. Public anonymous or confidential report; force confidential for conduct/uncertain sensitive cases regardless of selected category. Show safe clarification/preview, never reveal others' private evidence. Backend revalidates at submit; preview is not authority.
5. Confirm create/join and show reference, department, status, priority and explanation. Track under My Reports.

## Screens
| View | Content and actions |
|---|---|
| Community | General and 6 department filters, category/status/priority, search, priority/trending/newest/support sorting, counts, issue cards/table, approved safe evidence, 2nd/Disagree |
| Submit report | Dynamic fields, Other, clarification, attachments/privacy, preview and submit |
| My Reports | Own submitted/joined issues and confidential own cases, timeline, evidence, confirm/dispute when eligible |
| My Profile | Verification badge, own trust score and explainable event history, no identity details |
| Staff | Own department management queue only, priority explanation, status transitions, permitted private evidence, resolution attempt |
| Admin | All ordinary queues, stats, moderation, adjudication, unknown-location triage, AI summary, metrics |
| Confidential inbox | Explicit capability required, safe redacted case details, private evidence and follow-up; no public vote |
| Demo toolbar | Switch synthetic user, create student, reset with confirmation, advance time, simulate provider outage; visible only demo |

Active issue buttons 2nd / Disagree; resolution buttons Confirm Fix / Still Unresolved. Distinguish awaiting verification from verified closed. Do not show identities, handles, user links or voter lists. Show aggregate counts only; own vote may be shown. Staff does not get other department queues; public board access policy is student/admin, staff own management view plus safe public board if needed (no other staff queue data).

## UX acceptance
Clear loading/empty/error states; no fake actions; invalid fields explain remediation. UI and API permission checks both exist, API authoritative. No browser storage of sensitive attachments, identifiers or auth tokens. Clear client cache on logout/switch/reset and stale requests. Keyboard labels, focus, responsive tables, readable status badges, no color-only states. Build compiled assets and serve via FastAPI same-origin, no external CDN required. Final Playwright verifies full flows.
