We are now entering the final implementation sprint for ReportFix. Time is extremely limited.

You are explicitly authorized to finish Stages 04–10 together. This overrides previous instructions prohibiting frontend development before complete backend verification.

The objective is to deliver a polished, genuinely working application that we can immediately demonstrate to judges.

Do not waste time on extensive planning, documentation, repetitive tests, architectural refactoring or unnecessary abstractions.

## 1. Frontend foundation — IMPORT, DO NOT REINVENT

Use this existing open-source frontend:

https://github.com/satnaing/shadcn-admin

Reuse its existing layout, navigation, sidebar, tables, cards, charts, forms, dialogs, icons, typography and dark/light themes.

Additional components, only when necessary:
- https://github.com/shadcn-ui/ui
- https://github.com/TanStack/table
- https://github.com/recharts/recharts

If importing the entire template causes dependency or integration problems, extract its useful components and layout immediately. Do not spend excessive time fixing unrelated template code.

Remove all irrelevant template pages and dummy business data.

The application should be branded as:

**ReportFix**
Military College of Signals
Anonymous Campus Reporting & Resolution Platform

Use a professional, clean institutional design. Avoid excessive gradients, animations and decorative graphics.

## 2. Three fully functional user experiences

Use one shared application with role-specific dashboards and navigation.

### STUDENT

Sidebar:
- Community Dashboard
- Submit Complaint
- My Reports
- Trending
- My Profile

Community Dashboard:
- Total active complaints.
- Critical complaints.
- Issues resolved.
- Community participation.
- Search bar.
- General, EE, CSE, IS, Library, Cafeteria and Labs filters.
- Category, priority and status filters.
- Sorting by priority, trending, newest and most supported.
- Complaint cards or tables with clear status and priority indicators.
- Anonymous 2nd and Disagree buttons.
- Approved public evidence previews.
- Issue detail dialog or page.
- No reporter or voter identities.

Submit Complaint:
- Hierarchical category, subcategory and specific problem selection.
- Other option allowing completely unstructured text.
- Department and location selections.
- Additional details.
- English and Roman Urdu support.
- Classification preview and clarification.
- Anonymous public or confidential reporting.
- File and image uploads.
- Attachment as complaint or supporting evidence.
- Ask about visible faces first, followed by NSFW and sensitive content.
- Explicit public/private evidence consent.
- Disable public sharing when faces, sensitivity, uncertainty or confidentiality are present.
- Show the actual submission outcome, including grouped, submitted, confidential or clarification required.

My Reports:
- Submitted and joined complaints.
- Actual status and resolution history.
- Private confidential report tracking.
- Confirm Fix and Still Unresolved buttons when eligible.
- Resolution voting countdown.
- Relevant attachment information.

My Profile:
- Anonymous account.
- Verification status, clearly labeled synthetic for demo accounts.
- Trust score.
- Trust history and explanations.

### DEPARTMENT STAFF

Sidebar:
- Department Overview
- Complaint Queue
- Resolution Verification
- Completed Issues

Dashboard:
- Department name.
- Active issues.
- Critical issues.
- Pending verification.
- Reopened issues.
- Resolved issues.
- Prioritized complaint queue.
- Search and status/category/priority filters.

Complaint management:
- View relevant complaint details.
- View authorized supporting evidence.
- Acknowledge complaints.
- Mark In Progress.
- Mark resolved and initiate student verification.
- View aggregate confirmation/dispute counts.
- Display reopened complaints prominently.
- Display issue history.

Staff must only manage their assigned department.

### ADMINISTRATOR

Sidebar:
- Overview
- All Complaints
- Department Analytics
- Trending
- Moderation
- Confidential Inbox, only when authorized
- AI Summary

Dashboard:
- Total complaints.
- Active and resolved complaints.
- Critical issues.
- Reopened issues.
- Department-wise complaint distribution.
- Category distribution.
- Priority distribution.
- Resolution statistics.
- AI versus conventional processing statistics, using actual recorded metrics.
- Recent activity.

Management:
- All ordinary departmental queues.
- Complaint status management where permitted.
- Evidence review.
- Anonymous adjudication and trust adjustments through existing APIs.
- Suspicious activity and moderation flags.
- Confidential case management with restricted access.
- AI-generated administrative summary.

Use imported Recharts components and existing dashboard cards.

Never expose individual reporter identities, voter identities, emails or internal identity tokens.

## 3. Mandatory judge toolbar

Create a highly visible toolbar accessible throughout the isolated demo application.

It must support:
- Switching instantly between available synthetic students.
- Switching between staff from all six departments.
- Switching to administrator and confidential-handler accounts.
- Creating a new synthetic student instantly.
- Resetting the demo.
- Advancing simulated time.
- Simulating AI availability and failure.

Use the existing demo endpoints and local operator capability mechanism.

Provide an easy initial demo bootstrap screen or safe local launch mechanism. Never hardcode the operator token into frontend source or bypass the existing authorization checks.

Clear frontend caches and private data whenever accounts switch, logout or reset.

Judges must not have to use Swagger or PowerShell during the presentation.

## 4. Complete the remaining backend features quickly

Inspect the actual existing backend and OpenAPI schema before wiring the frontend.

Most of Stages 04–06 are already implemented. Fix only critical issues discovered during integration.

Do not rewrite the existing backend.

Ensure the complete report → grouping → department → resolution → dispute → reopening workflow functions.

Where a required frontend feature lacks an API, add the smallest functional backend endpoint necessary.

### Bonus A — Trending board

Implement immediately.

If a dedicated trending endpoint does not exist, calculate a useful trending ranking from available public issue data.

Prefer the documented recent weighted participation formula where timestamps and weights are available.

Use a minimal backend aggregation endpoint if required.

Show:
- Trending complaints.
- Most supported active issues.
- Department-wise activity.
- Recent increases in participation.

Never include confidential complaints.

### Bonus B — AI administrator summary

Implement a minimal backend summary endpoint using the existing working Azure adapter.

Use GPT-5.4 Nano or Mini.

Generate actual statistics using conventional code, then send only sanitized non-confidential aggregate information to AI.

Display:
- Most affected departments.
- Critical unresolved complaints.
- Major recurring problems.
- Reopened issues.
- Recommended administrative priorities.

Provide a clearly labeled conventional fallback when AI is unavailable.

Never fabricate an AI-generated summary.

### Bonus C — Spam and brigading detection

Implement simple deterministic checks using existing database records:
- Repeated submissions.
- Excessive submission frequency.
- Duplicate voting attempts.
- Multiple newly created accounts voting together.
- Suspicious coordinated activity.

Expose actual flags in the administrator dashboard.

Use simple SQL queries and timestamps. No additional machine-learning libraries.

Do not automatically punish students based solely on suspicious patterns.

### Additional frontend enhancements

Use actual backend data to provide:
- Department activity charts.
- Resolution performance.
- Complaint category charts.
- Priority distribution.
- Recent activity.
- Trust history visualization.
- Actual AI processing statistics.
- Search, filtering and sorting.
- Status timelines.

These enhancements should require little or no additional backend functionality.

## 5. Vision and attachments

The current attachment implementation includes private uploads and a manual-review fallback.

If Featherless vision integration can be completed quickly using existing credentials and a verified available model, implement it.

Otherwise, retain the functional manual image classification and review workflow.

Do not allow vision integration to delay the entire product.

Do not claim automated face or NSFW detection is functional unless it actually works.

Unreviewed, sensitive or uncertain attachments remain private.

## 6. Shortcuts explicitly permitted

We need to finish the application now.

You may:
- Use synthetic demonstration accounts.
- Use synthetic complaints and safe example evidence.
- Use existing seed data and extend it for a convincing dashboard.
- Use standard imported UI components without custom styling.
- Calculate visual analytics from existing public or authorized API responses.
- Use simple dialogs instead of creating separate complex pages.
- Use manual evidence review instead of unavailable automated inspection.
- Use polling instead of WebSockets.
- Use a straightforward shared dashboard layout.
- Reuse existing code and consolidate small modules.

You may not:
- Fake mandatory backend functionality.
- Display invented statistics as actual application data.
- Fake AI responses.
- Bypass role restrictions or confidential attachment protections.
- Hardcode credentials.
- Present simulated verification as real institutional verification.

## 7. Local execution

The application must run locally on the existing Windows development environment.

Serve the compiled frontend through FastAPI on the same origin, preferably:

http://127.0.0.1:8000

Preserve the existing origin and session security behavior.

Ensure SPA navigation does not intercept API endpoints.

Create a simple Windows PowerShell launcher, such as START.ps1, that handles the necessary local setup, migration, demo seed and application startup.

Ideally, one command should start the complete application.

Keep all dependencies and assets local after installation.

No Render, Docker, cloud deployment or additional infrastructure.

## 8. Minimum final verification

Do not create dozens of new tests.

Run a practical end-to-end smoke check covering:
1. Start the application and load the actual frontend.
2. Switch to a student and submit a complaint.
3. Submit an equivalent complaint from another student and verify grouping.
4. Verify critical safety priority.
5. Switch to the assigned department staff and mark the complaint resolved.
6. Switch to affected students and dispute the resolution to reopen it.
7. Verify confidential complaints remain absent from the public dashboard.
8. Verify an attachment can be uploaded and private evidence stays protected.
9. Check the administrator dashboard and available bonuses.
10. Verify judge reset restores a working demonstration.

Build the frontend and run the existing backend suite once if time permits.

Fix presentation-blocking defects immediately. Ignore minor warnings and noncritical cosmetic defects.

## 9. Prepare the presentation

Populate the demo database with clearly synthetic examples covering all six departments.

Include:
- Network issues.
- Projector malfunction.
- Library AC failure.
- Electrical safety hazard.
- Cafeteria complaint.
- A complaint awaiting verification.
- A reopened complaint.
- A confidential case.
- Students with different trust scores.

Prepare a short DEMO.md containing:

- Exact application startup command.
- Browser URL.
- How to access judge controls.
- A reliable demonstration sequence.
- A two-minute pitch divided between three speakers.
- Implemented mandatory requirements.
- Implemented bonuses.
- Honest remaining limitations.

The pitch must emphasize:
- Conventional code handles decisions, security, voting, priority and trust.
- AI handles difficult language understanding.
- The same issue is grouped across different languages.
- Student identities remain hidden from ordinary application users.
- Departments cannot falsely resolve complaints without community accountability.

## 10. Final stopping point

Finish the actual working application before writing the completion report.

Update PROGRESS.md honestly.

Audit all changes for credentials and private information, commit and push the safe project files to main.

Return only:
- Application startup command.
- Local browser URL.
- Features working.
- Bonuses working.
- Remaining limitations.
- Actual test/build results.
- GitHub commit hash.

Do not spend time on an extensive development report.

STOP — ReportFix is ready for final demonstration, or explicitly identify any remaining presentation-blocking failure.