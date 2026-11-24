# Sequential implementation roadmap

One stage per explicit user message. No frontend until Stage 10. Approximate coding budgets are aggressive planning targets, not promises; test gates take precedence. Do not start later stage until prior stage passes and user authorizes. See each stage file for scope, deliverables, tests and STOP gate; prompts directory contains separate ready-to-copy prompts.

| Stage | Objective | Budget | Depends on |
|---|---|---:|---|
| 00 | Foundation, interfaces, configuration | 3 min | none |
| 01 | Schema, seed and registry | 4 min | 00 |
| 02 | Identity, permissions, demo controls | 5 min | 01 |
| 03 | Complaint intelligence, location, privacy | 8 min | 02 |
| 04 | Grouping, priority, query API | 5 min | 03 |
| 05 | Community, lifecycle, trust | 8 min | 04 |
| 06 | Attachment pipeline and review | 7 min | 05 |
| 07 | All bonus features | 4 min | 06 |
| 08 | Optional live vision | 3 min | 07 |
| 09 | Backend hardening, API freeze, local run | 5 min | 08 |
| 10 | Import frontend, connect and test | 8 min | 09 |

Total 60 min target; use remaining hackathon time to fix attacks and prepare demo. Optional external providers may be configured later but must be honestly marked not live-tested, with working fallback and no mock claims. If a required gate fails, stop and fix that stage before advancing. Stage 10 includes final regression and demo handover, not deployment.
