# Data model (SQLite)

Use SQLModel/SQLAlchemy and Alembic. All timestamps UTC; display Pakistan time. Opaque UUID IDs, FK enforcement, indexes for department/status/location/time, write locks/transactions. Never serialize internal user associations. Sensitive identity and owner mapping not exposed. Seed only synthetic data, separate runtime from test DB. Stage 1 schema may reserve later fields but no later business logic.

| Entity | Fields / constraints (minimum) |
|---|---|
| users | id, role, dept nullable, confidential_capability, verified, demo, created_at, trust_cache (0..100); role/dept checks |
| verified_identities | token unique, user_id unique FK, created_at; HMAC only |
| verification_challenges | token, OTP digest, expiry, attempts, consumed, last_sent; TTL cleanup |
| sessions | token_digest unique, user_id, expiry, demo_operator capability, generation |
| departments | six fixed codes PK, label |
| locations | id, parent_id, dept_id, name, demo, active; unique canonical path |
| location_aliases | location_id, normalized alias; unique pair, ambiguous alias supported |
| categories | id, parent_id, code, label, active; unique sibling code |
| issues | id, department_id, location_id, category/subtype/failure/asset, safe_title/description, impact/hazard, status, fingerprint nullable, recurrence_of, created/updated, active_unresolved_seconds, active_since, version; unique active specific fingerprint |
| reports | id, owner_id private, issue_id nullable, private input if needed, safe extracted fields, clarification state, created, request_key; unique owner/request_key |
| community_votes | issue_id, user_id, choice, created/updated, valid; unique issue/user |
| issue_participants | issue_id, user_id, source, first_joined, valid; unique issue/user; no duplicate crowd count |
| resolution_rounds | id, issue_id, sequence, opened_at, deadline, state/outcome, finalized_at; unique issue/sequence and one open round |
| voter_eligibility | round_id, user_id, frozen_weight, valid; unique round/user |
| resolution_votes | round_id, user_id, choice, valid, timestamps; unique round/user; composite FK eligibility |
| trust_events | id, user_id, unique event_key, delta, reason, source_ref, evidence_ref, created_at; immutable, compensating reversal |
| issue_history | issue/case ref, action, status, safe reason, timestamp, private actor ref where needed |
| attachments | id, owner_id, report/case nullable, purpose, safe type, size, checksum, private storage key, sanitized key, declared_faces/nsfw/sensitive, public_requested, external_consent, state, expiry, timestamps |
| attachment_reviews | attachment_id, local face result, review flags, reviewer private ref, safe reason, timestamp; audit changes |
| confidential_cases | id, safe case content restricted, status, hazard, timestamps; no author field exposed |
| confidential_ownership | case_id, user_id, unique case/owner; private association |
| moderation_flags | id, issue/case ref, rule, cluster key unique, private evidence, state, reason, timestamps |
| processing_events | report ref if safe, kind, mode, provider label, success/error class, latency, created; no raw content |
| audit_logs | event, actor private ref if required, target opaque ref, safe reason, time; never expose identities |
| system_settings | key unique, validated value; demo clock/generation and versioned thresholds |

Status/role/visibility enums in shared schema; no invalid state transitions via generic update. For public issue privacy escalation remove from ordinary access and move to restricted record atomically; keep internal history but redact exposure. Index votes by time for cluster detection. Prefer derived counts and priority, trust ledger is source of truth; cache only transactionally. Reset seed with fixed synthetic accounts, realistic low/medium/high/critical sample issues, one pending round, restricted case, demo age distribution; no actual student identities or sensitive imagery.
