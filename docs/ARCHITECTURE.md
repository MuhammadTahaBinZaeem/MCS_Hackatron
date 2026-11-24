# Architecture — local modular monolith

Python 3.12, FastAPI, SQLModel/SQLAlchemy, Pydantic, SQLite, Alembic, uv. React/TS/Vite/Shadcn Admin only at final stage. One process bound to 127.0.0.1, local disk outside static assets, no deployment infrastructure. Local browser communicates with `/api/v1`; final compiled frontend served same origin. Separate Vite dev server only loopback with proxy. Use one worker for demo; DB transactions still required. Enable SQLite foreign keys, WAL, busy timeout; use write serialization (`BEGIN IMMEDIATE` or equivalent) for read-then-write grouping, votes, resolution and reset. Avoid network calls inside write transaction.

```text
backend/app/
  main.py config.py database.py
  models/ schemas/ api/ repositories/ services/ security/
  engines/ classification.py routing.py location.py duplicates.py
           priority.py reputation.py voting.py lifecycle.py moderation.py trending.py
  providers/ text/ vision/ storage/ email/
  attachments/ validation.py sanitizer.py face_detection.py privacy.py extraction.py
backend/data/  # versioned synthetic seed/taxonomy/aliases only
backend/migrations/ backend/tests/{unit,integration,adversarial}/
frontend/       # absent until Stage 10
tests/e2e/ scripts/ docs/ prompts/ AGENTS.md .env.example pyproject.toml
runtime/        # ignored, absolute resolved local root; database/uploads/secrets/logs
```

## Boundaries
- API authenticates session, validates DTO, calls service; no raw ORM models in responses.
- Services coordinate privacy screening, classification, registry validation, duplicate matching and atomic persistence. Engines are pure where possible and accept explicit clock/config. Privacy screening happens before any external processing or public write. Report preview cannot grant permission to publish.
- TextProvider classify/compare/summarize returns structured typed suggestion or explicit failure. VisionProvider analyze returns suggestions or NOT_CONFIGURED; no fake success. StorageProvider save/read/delete within private local root, generated IDs, no client paths. EmailProvider send OTP or explicit demo implementation. Inject providers and clock in tests.
- Audit events capture decision reason codes, timestamps and anonymous case references; sensitive content, identity token and voter identities never in exposed logs. Admin adjudication identifies report by opaque case ref, not person. Service-only mapping remains private.
- Separate data visibility: public DTO, own DTO, staff DTO, restricted confidential DTO; public search/trending/summary source only public safe records. Confidential case and owner association separate. Reclassification revokes public access and prior attachment approvals atomically; avoid cache leakage.
- All external calls bounded deadline, disabled by default until config; no requirement for internet to start. Provider errors yield typed clarification/manual path. Use local metrics; no telemetry.

## Transaction patterns
Validate -> authorize -> prepare safe data outside transaction -> begin write -> re-check authorization/current version/fingerprint -> write issue/participants/history atomically -> commit. Use unique keys and idempotency; retry safe SQLite busy errors bounded, else return controlled conflict. Attachment filesystem/DB cannot share transaction: quarantine then persist metadata; compensate on failed writes, clean orphans. Reset holds exclusive application lock and invalidates sessions and pending requests; no real data touched. Inject Clock for 48h expiry; run expiration on reads/mutations or local periodic task; no external scheduler.
