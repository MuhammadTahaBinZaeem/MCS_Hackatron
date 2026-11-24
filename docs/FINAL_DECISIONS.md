# Final decisions — v1.1 (locked)

| Topic | Decision |
|---|---|
| Scope | Local laptop only, synthetic competition data; external AI/SMTP optional |
| Departments | EE, CSE, IS, Library, Cafeteria, Labs; General is all-department filter |
| Form | One hierarchical guided form; Other supports entirely plain text, no required preselection; same pipeline |
| Locations | Configurable registry; official names only if confirmed; illustrative Lab 3/4 etc explicitly demo |
| Identity | Random private account ID, university email OTP, retained HMAC uniqueness token, no raw email after OTP; one canonical email per student assumption |
| Public anonymity | No reporter/voter identity on any board/API; private ownership for own history, votes and trust; pseudonymity not cryptographic unlinkability |
| Roles | Student, staff, admin, confidential-handler capability; demo operator separate |
| Active voting | 2nd / Disagree, one current vote, no reporter self-vote; 2nd means affected |
| Fix voting | Confirm Fix / Still Unresolved, original reporter eligible, frozen roster and weight; 48h window, immediate votes |
| Reopen | >=2 distinct disputes, dispute weight >=1.5, >=60% cast weight; solo dispute -> review |
| Close | All eligible confirm -> immediate verified close; otherwise at expiry >=60% eligible weight confirms, >=2 confirms (or sole eligible confirms), no outstanding dispute; else review |
| Trust | 0–100, start 50, event ledger, weight 0.5+trust/100; independent verification only |
| Priority | Base impact + bounded crowd + unresolved aging, critical safety override 100 |
| Grouping | Canonical location/category/asset/failure plus semantic matching; no cross-location or confidential public merges |
| Evidence | JPEG/PNG/WebP/PDF/TXT, attachment as complaint or evidence; private by default, faces/NSFW/sensitive/uncertain never public |
| AI | Rules first; GPT-5.4-nano, mini, full and optional gpt-5.6-luna deployment; exact names configured and probed; Featherless optional text/vision |
| Vision | Interface present Stage 0; implement live adapter Stage 8; manual review fallback |
| Bonuses | Trending, AI-written admin summary, spam/brigading detection; processing metrics |
| Stack | Python 3.12/FastAPI/SQLModel/SQLite/Alembic/uv; React/Vite/TS/Shadcn Admin imported only Stage 10 |
| Storage | Private local filesystem, sanitized derivatives and authorized downloads |
| Testing | Stage gates + pytest/Hypothesis + final Playwright; no fabricated results |
| Deployment | None; local launch only; no public network binding |

MCS context is a demo context, not a verified campus directory or official institutional service. Do not upload restricted institutional material. Real SMTP and provider capability depend on supplied configuration. Aim for all nine requirements and bonuses; report actual coverage, not promised marks. Detailed policies in RULES, SECURITY, AI and TESTING.
