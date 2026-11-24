# Reuse inventory

Use package managers, not wholesale copies of backend applications. Pin compatible resolved versions in lockfiles. Verify upstream LICENSE at chosen revision, transitive dependencies and model weights separately; record package, URL, version/commit, license and notices in THIRD_PARTY_NOTICES.md. MIT/Apache typically require retained notices, not visible UI branding. No dependency should be assumed licensed merely because GitHub hosts it.

| Repo | Use | Stage |
|---|---|---|
| https://github.com/fastapi/fastapi | REST and OpenAPI | 0 |
| https://github.com/fastapi/sqlmodel | ORM | 1 |
| https://github.com/sqlalchemy/alembic | migrations | 0–1 |
| https://github.com/pydantic/pydantic | typed validation | 0 |
| https://github.com/rapidfuzz/RapidFuzz | typo/alias similarity | 3 |
| https://github.com/openai/openai-python | API provider adapters | 3,8 |
| https://github.com/pytest-dev/pytest | regression tests | 0 |
| https://github.com/HypothesisWorks/hypothesis | property tests | 0 |
| https://github.com/python-pillow/Pillow | image validation/re-encode | 6 |
| https://github.com/opencv/opencv | local face detection | 6 |
| https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet | YuNet detector; check model license | 6 |
| https://github.com/py-pdf/pypdf | PDF extraction | 6 |
| https://github.com/h2non/filetype.py | optional signature detection | 6 |
| https://github.com/microsoft/presidio | optional redaction, not mandatory heavyweight install | 6 |
| https://github.com/Cisco-Talos/clamav | optional local malware scan | 6 |
| https://github.com/satnaing/shadcn-admin | primary UI foundation, import only at stage 10 | 10 |
| https://github.com/shadcn-ui/ui | reuse components as needed | 10 |
| https://github.com/TanStack/table | filters/table (prefer template's existing dependency) | 10 |
| https://github.com/TanStack/query | server state (prefer existing) | 10 |
| https://github.com/react-hook-form/react-hook-form | forms | 10 |
| https://github.com/recharts/recharts | charts | 10 |
| https://github.com/lucide-icons/lucide | icons | 10 |
| https://github.com/microsoft/playwright | final browser tests | 10 |

Use Python stdlib secrets/hmac/hashlib/math/pathlib/sqlite-compatible utilities for identity and algorithms. No mandatory embeddings, vector database, full helpdesk import, separate state-machine dependency, Redis or cloud SDK. Optional extras must not break local startup. If chosen template revision incompatible, select a known compatible revision or another MIT dashboard with explicit reason; do not build UI from scratch. Record source commit, remove nested git metadata without losing upstream attribution, preserve license and third-party assets licenses. Do not fetch arbitrary code without inspecting it.
