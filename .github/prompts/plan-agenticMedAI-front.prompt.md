Plan: Production-Grade Frontend Overhaul
TL;DR: Fix existing bugs (theme toggle, sidebar tabs), overhaul all HTML semantics and accessibility, build a typed API client layer aligned with the backend's Pydantic schemas, add a full JWT-ready authentication system (login/register/protected routes), connect every page to the backend's 9 endpoints, create a full admin dashboard (patient management, report audit, system health, usage monitor), and add error boundaries, loading states, and proper documentation throughout. All changes confined to frontend.
Phase 1 — Bug Fixes (Quick Wins)
Theme toggle "System" button: The third button (Monitor icon) sets theme to "system" — it follows the OS preference via prefers-color-scheme. It does work, but there's no user-visible feedback distinguishing it from the active light/dark state. Fix: Add tooltips via aria-label and a visible label on hover. The resolvedTheme state already tracks the result, but the UI doesn't show "System (Dark)" or "System (Light)". Add a subtle label below or a tooltip.

Evidence panel tabs overflow: The 4 tabs (Evidence, Findings, History, Guidelines) in CitationsSidebar.tsx use px-3 padding in a w-80 (320px) sidebar with px-2 container padding. The combined width of tabs + icons + gaps exceeds the available space. Fix: Use flex-1 or flex-shrink on each tab so they share available width equally, switch to icon-only at narrow widths with tooltips, and add overflow-x-auto as a safety fallback.
Phase 2 — HTML Semantics & Accessibility Overhaul
Replace dangerouslySetInnerHTML in ChatMessage.tsx: Current code injects raw HTML for bold/emoji rendering — XSS vulnerability. Replace with a safe inline parser (simple regex-to-React-elements function) or integrate react-markdown as a dependency.

Semantic <time> elements: All date displays across timeline page, case page, and ChatMessage.tsx should use <time datetime="ISO">formatted</time> instead of plain <span>.

Semantic structure for timeline: The timeline event list in timeline/[patientId]/page.tsx should use <ol> / <li> instead of nested <div> elements. Each year group should be a <section> with a proper heading.

<section> and <article> for case page: The diagnosis banner, findings panel, treatment plan, reasoning trace, and historical context in case/[id]/page.tsx should each be wrapped in <section aria-labelledby="..."> with matching heading IDs.

Replace clickable <div> elements with <button> or <details>: Citation cards in CitationsSidebar.tsx line 150 use <div onClick> — not keyboard accessible. Switch to native <button> or <details>/<summary>.

Add skip-to-content link in layout.tsx: Insert a visually hidden skip navigation link for keyboard users.
Add aria-label to all icon-only buttons: Every button that only contains an icon (sidebar toggles in agent page, zoom/reset in ImageViewer, settings, back arrows, close button on sidebar) needs an explicit aria-label.

Attach menu keyboard support in ChatInput.tsx: Add aria-expanded, aria-haspopup="menu", Escape-to-close, and role="menu" / role="menuitem" on the dropdown items.

Add aria-live="polite" to AgentStatusIndicator.tsx: Status changes should be announced to screen readers.

Add <label> elements: Link labels to the chat textarea, the approval notes textarea in ApprovalBar.tsx, and the hidden file input.

Add aria-pressed to toggle buttons: Heatmap/Regions toggles in ImageViewer.tsx should communicate pressed state.

Add prefers-reduced-motion guard: Wrap all CSS animations with @media (prefers-reduced-motion: reduce) to disable them for motion-sensitive users.
Phase 3 — TypeScript & Code Quality
Remove unused SidebarTab from types.ts: It conflicts with the local type in CitationsSidebar.tsx.

Fix handleSend signature mismatch: agent/page.tsx handleSend(text: string) ignores the File[] attachment param from ChatInput.onSend. Either handle files or update the types to match.

Add explicit return types to all page components and major sub-components.

Create React Error Boundary component: Add a reusable ErrorBoundary in components/shared/ and wrap it at the layout level and around major page sections (image viewer, chat area, etc.).

Add loading.tsx files for every route segment (/agent/loading.tsx, /case/[id]/loading.tsx, /timeline/[patientId]/loading.tsx) per Next.js conventions.

Wire suggested prompts in ChatArea.tsx: The 4 prompt buttons have no onClick. Add an onPromptClick callback that inserts the text into the chat input.

Disable/label non-functional buttons: The Mic button and Settings button should either be implemented or marked as "Coming soon" with disabled + tooltip.

Phase 4 — API Client Layer
Create frontend/src/lib/api/client.ts: A typed HTTP client class wrapping fetch() with:

Base URL from env var NEXT_PUBLIC_API_URL (default http://localhost:8000/api/v1)
Automatic Authorization: Bearer <token> header injection
Typed request/response methods for every backend endpoint
Error handling with typed error responses
Request/response interceptors for auth token refresh
Create frontend/src/lib/api/types.ts: Frontend-aligned types that mirror the backend Pydantic schemas exactly:

CaseAnalysisRequest / CaseAnalysisResponse ← from schemas.py
ReportApprovalRequest / ReportApprovalResponse
PatientCreateRequest / PatientSummary / PatientListResponse
TimelineEventResponse / PatientTimelineResponse
ReportSummary / PatientReportsResponse
HealthResponse
Enums: ApprovalStatus, Severity, Gender, EncounterType, Modality, JudgeVerdict, ToolName
Create custom React hooks (frontend/src/hooks/):

usePatients() — fetches patient list, provides create/refresh
usePatient(id) — fetches single patient
useTimeline(patientId) — fetches timeline events
usePatientReports(patientId) — fetches reports for patient
useReport(reportId) — fetches single report
useCaseAnalysis() — submits a case for analysis, tracks loading state
useReportApproval() — sends approve/reject/edit
useHealthCheck() — polls system health
Create frontend/.env.local template and add NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1.

Phase 5 — Authentication System
Create frontend/src/providers/AuthProvider.tsx: A context provider managing:

user state (id, name, email, role)
token stored in localStorage (with secure httpOnly cookie upgrade path documented)
login(email, password) → calls POST /api/v1/auth/login (will 404 until backend adds it — graceful fallback)
register(name, email, password) → calls POST /api/v1/auth/register
logout() → clears token, redirects to login
isAuthenticated boolean
Token expiry checking and auto-logout
Create frontend/src/app/auth/login/page.tsx: Production-grade login page with:

Email + password fields with validation
Loading state during submission
Error messages (invalid credentials, network error)
Link to register page
Consistent with the design system (glass cards, gradient accents)
<form> with proper <label> elements
Create frontend/src/app/auth/register/page.tsx: Registration page with:

Name, email, password, confirm password fields
Client-side validation (email format, password strength, match)
Specialization/role field (GP, Radiologist, Surgeon, etc.)
Terms acknowledgement checkbox
Link to login page
Create frontend/src/components/auth/ProtectedRoute.tsx: A wrapper component that:

Checks AuthProvider context for valid session
Redirects to /auth/login if unauthenticated
Shows loading skeleton while checking
Wrap all protected routes (/agent, /case/*, /timeline/*, /admin/*) with the ProtectedRoute guard. Landing page (/) remains public.

Update Navbar.tsx: Show user avatar + name when logged in, Login button when not. Add a user dropdown menu with Profile, Settings, Logout options.

Phase 6 — Connect Pages to Backend
Agent page → Backend integration:

Replace mock simulation with useCaseAnalysis() hook calling POST /api/v1/cases/analyze
Map CaseAnalysisResponse to chat messages and citations
Keep mock fallback when backend is unreachable (graceful degradation)
Show real tool results from specialist_summaries
Case page → Backend integration:

Use useReport(id) to fetch real report from GET /api/v1/cases/reports/{id}
Wire Approve/Reject/Edit buttons to POST /api/v1/cases/approve via useReportApproval()
Map CaseAnalysisResponse → existing UI components

Timeline page → Backend integration:

Use usePatient(patientId) + useTimeline(patientId) to fetch real data
Map PatientTimelineResponse.events to existing TimelineEvent UI type
Show loading skeleton while fetching
Create patient list page (/patients): New page displaying all patients from GET /api/v1/patients. Each patient card links to their timeline. Include a "Create Patient" form using POST /api/v1/patients.

Phase 7 — Admin Dashboard
Create frontend/src/app/admin/page.tsx: Full admin dashboard with 4 sections:

System Health: Poll GET /api/v1/health, display status, version, registered tools, debug mode. Green/red status indicators.
Patient Management: Table of all patients from GET /api/v1/patients with name, DOB, MRN, created date. Create patient button.
Report Audit Log: All reports across patients (calls GET /api/v1/patients/{id}/reports for each patient), showing diagnosis, confidence, approval status, timestamps. Filter by status.
Usage Monitor: Display estimated API cost based on number of cases analyzed (static calculation based on plan's cost estimates — $0.02-0.05 per case).
Create admin layout (/admin/layout.tsx): Admin-specific layout with sidebar navigation for the 4 dashboard sections.

Protect admin routes: Add role-based guard (only admin role can access /admin/*).

Phase 8 — Polish & Documentation
Add not-found.tsx for the app root — styled 404 page consistent with design system.

Add JSDoc comments to all exported functions, hooks, providers, and major components.

Phase 8 — Polish & Documentation
Add not-found.tsx for the app root — styled 404 page consistent with design system.

Add JSDoc comments to all exported functions, hooks, providers, and major components.

Create frontend/README.md documenting:

Setup instructions (npm install, env vars, npm run dev)
Architecture overview (pages, components, hooks, providers)
API client usage
Auth system overview
How to connect to backend
Component structure diagram
Create frontend/src/lib/constants.ts: Centralize all magic strings (API paths, route paths, localStorage keys, default values).
Verification

cd frontend && npx next build — must compile with zero errors
All pages render correctly in both light and dark modes
Keyboard-only navigation works through all interactive elements
Auth flow: Register → Login → Protected page access → Logout → Redirect to login
With backend running (uvicorn medai.main:app): patient list loads, case analysis submits, reports load, approval works
Without backend: graceful fallback to mock data or error state (no crashes)
npx next lint passes
Every <button> has visible text or aria-label, every <input> has <label>, every <img> has alt
Decisions

Auth storage: JWT in localStorage for MVP, with documented upgrade path to httpOnly cookies. Backend auth endpoints don't exist yet — API client will handle 404 gracefully and docs will specify the contract needed.
API client pattern: Class-based singleton (ApiClient) rather than individual fetch calls — centralizes error handling, auth headers, and base URL config. Follows the repository research patterns from the backend's clean architecture.
No react-markdown heavy dependency: Instead, create a lightweight MarkdownRenderer component with regex-based safe parsing for bold, headings, and lists — avoids bundle bloat and the XSS risk of dangerouslySetInnerHTML.
Admin dashboard scope: Read-only for reports and patients (uses existing GET endpoints). Patient creation allowed via existing POST endpoint. No user management CRUD until backend auth exists.
Keep mock data as fallback: All hooks will attempt real API calls first, fall back to mock data if the backend returns errors — ensures the demo always works.
Backend Suggestions (DO NOT IMPLEMENT — for teammate reference)

After reviewing the backend codebase, here are recommendations for the backend team:

Add auth endpoints: The frontend expects POST /api/v1/auth/register (name, email, password, specialization) and POST /api/v1/auth/login (email, password) returning { token, user }. Consider python-jose for JWT or passlib for password hashing. Add a User entity to domain/entities.py.

Restrict CORS: main.py has allow_origins=["*"] — should be ["http://localhost:3000", "https://your-production-domain.com"].

Add rate limiting: Consider slowapi or a middleware to prevent budget exhaustion via API abuse.

Switch from in-memory to persistent storage: The in-memory repositories in memory.py lose all data on restart. SQLAlchemy + asyncpg are already listed as optional deps in pyproject.toml — wire them in.

Add request validation middleware: Input sanitization for clinical text fields to prevent injection attacks.

Add /api/v1/auth/me endpoint: For the frontend to validate tokens and fetch current user profile on page load.

Add WebSocket for streaming: The case analysis can take 5-10s with real models. A WebSocket or SSE endpoint for POST /cases/analyze would enable real-time progress updates (tool by tool) instead of a single blocking response.

Add pagination: GET /patients and report list endpoints should support ?limit=&offset= query params for scalability.







