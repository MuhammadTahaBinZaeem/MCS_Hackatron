# API contract — /api/v1

JSON DTOs, Pydantic strict validation; list pagination (default 25 max 100), safe search/filter/sort allowlist. Uniform error {code,message,field_errors?,request_id}; 400 invalid semantics, 401 unauthenticated, 403 unauthorized, 404 for hidden resource, 409 stale/duplicate conflict, 413 size, 415 file type, 422 schema, 429 rate limit, 503 unavailable provider only when no safe fallback. Never return stack traces. Auth cookie, origin/CSRF checks. Idempotency keys for submission/upload/status, version for concurrent transitions. Return only role-specific fields.

| Method/path | Purpose/input/output |
|---|---|
| POST /auth/request-otp | email -> generic challenge response; no account enumeration |
| POST /auth/verify-otp | challenge/code -> session; no email echo |
| GET /auth/me; POST /auth/logout | role, verification, own trust; revoke session |
| GET /departments, /locations, /categories | registered hierarchy, filters, synthetic label |
| POST /reports/preview | structured fields or free text, staged attachment IDs, visibility -> safe proposals, priority reason, clarification, candidate issues; no write authority |
| POST /reports | same validated input + clarification/merge choice + idempotency -> issue/case reference, status, own safe view; revalidate all |
| GET /issues; GET /issues/{id} | sanitized ordinary list/detail, aggregate counts, own action eligibility; filters dept/category/status/priority/q/sort |
| POST /issues/{id}/vote | choice 2ND/DISAGREE -> effective own choice and counts; no identity list |
| GET /me/reports; GET /me/trust | own history and ledger only |
| GET /staff/queue | own department management list |
| PATCH /staff/issues/{id} | transition, reason, version -> safe history; resolution creates round |
| POST /issues/{id}/resolution-vote | round_id, CONFIRM/DISPUTE -> own vote and aggregate round outcome |
| POST /attachments | multipart file, purpose, declarations, consent -> staged ID/status; limits before decoding |
| GET /attachments/{id} | authorized safe bytes or denial; optional status endpoint |
| POST /attachments/{id}/review | authorized reviewer checklist/reason -> state; no bypass of consent/face rules |
| GET /admin/issues; GET /admin/statistics | all ordinary issues and safe aggregates |
| GET /admin/confidential; PATCH /admin/confidential/{id} | restricted cases and private workflow |
| GET /admin/moderation; POST /admin/moderation/{id}/decision | review and invalidate verified abuse with reason |
| POST /admin/adjudicate | opaque report/issue/round ref, outcome/evidence -> trust events; no voter identities |
| GET /trending; POST /admin/summary | trend list and AI or labeled deterministic summary |
| GET /demo/users; POST /demo/switch-user | synthetic list and switch; demo operator only |
| POST /demo/create-student; POST /demo/reset | synthetic student; reset and new operator session |
| POST /demo/advance-time; POST /demo/provider-mode | demo clock/provider failure controls |
| GET /healthz; GET /readyz | basic health, DB readiness, no secrets |

Use public issue DTO: opaque issue ID, safe title/summary, department/location/category, status, priority score/reason, aggregate second/disagree/affected counts, sanitized history, approved attachment refs, own permissions/vote. No actor IDs, raw content, identity token, email, filenames or per-user votes. Own views add own records only. Staff DTO adds allowed private evidence/operational fields, not identities. Confidential DTO restricted, content redacted where necessary. Clarification response explicit missing fields and registered options; unknown never silently routed. Freeze OpenAPI before frontend; generate types/client if useful. Prefix health endpoints may additionally be exposed at root for local scripts.
