## Plan: Full-Stack Integration Fix & Feature Completion

**TL;DR:** After the merge, the frontend won't compile — 3 files are missing (`store.ts`, `file-upload.ts`, `api/mappers.ts`), hooks have API shape mismatches, and the agent page hardcodes a mock patient. The backend works correctly with real Modal endpoints. Plan: fix all build errors → create missing modules → add patient selector to co-pilot → remove all mock fallbacks → add patient CRUD → fix navigation → enrich seed data → test end-to-end.

**Steps**

### Phase 1: Fix Build-Breaking Issues (Frontend Won't Compile)

1. **Create [frontend/src/lib/store.ts](frontend/src/lib/store.ts)** — Zustand stores:
   - `useChatStore`: state for `messages: ChatMessage[]`, `citations: Citation[]`, `agentStatus: AgentStatus`, `sidebarOpen: boolean`, `currentPatient: Patient | null`; actions: `addMessage`, `setMessages`, `setCitations`, `setAgentStatus`, `toggleSidebar`, `setCurrentPatient`, `reset`
   - `useUIStore`: state for `backendOnline: boolean`; action: `setBackendOnline`
   - Import types from `@/lib/types`

2. **Create [frontend/src/lib/file-upload.ts](frontend/src/lib/file-upload.ts)** — File utilities:
   - `filesToImageDataUrls(files: File[]): Promise<string[]>` — Filter image files, convert to base64 data URLs via FileReader
   - `filesToAudioDataUrls(files: File[]): Promise<string[]>` — Filter audio files, convert to base64 data URLs
   - `getFileCategory(file: File): "image" | "audio" | "document"` — categorize by MIME type

3. **Create [frontend/src/lib/api/mappers.ts](frontend/src/lib/api/mappers.ts)** — API→domain type mappers:
   - `mapApiPatient(p: ApiPatientSummary): Patient` — map `date_of_birth→dob`
   - `mapApiTimelineEvent(e: ApiTimelineEvent): TimelineEvent` — pass through with type normalization
   - `mapApiResponseToAIReport(r: ApiCaseAnalysisResponse): AIReport` — map flat response to `AIReport` shape (findings, reasoning trace, specialist outputs, judge verdict)
   - `mapApiFinding(f): Finding` — map API finding shape to `Finding` type
   - `mapApiReasoningTrace(trace): ReasoningStep[]` — map reasoning trace entries to `ReasoningStep[]`

4. **Rewrite [frontend/src/lib/hooks.ts](frontend/src/lib/hooks.ts)** — Replace custom `useAsync` pattern with React Query hooks (TanStack Query is already installed in `package.json`):
   - Wrap all queries in `useQuery()` — naturally provides `.isLoading`, `.data`, `.error` (Error object)
   - `usePatients()` → `useQuery({ queryKey: ['patients'], queryFn: () => apiClient.listPatients() })`
   - `usePatient(id)` → `useQuery` on `apiClient.getPatient(id)`
   - `useTimeline(patientId)` → aliased `useQuery` on `apiClient.getPatientTimeline(patientId)` (matching the import name used in timeline page)
   - `useReport(reportId)` → `useQuery` on `apiClient.getReport(reportId)`
   - `useCreatePatient()` → `useMutation({ mutationFn: apiClient.createPatient })` — provides `.mutate()`, `.isPending`
   - `useApproveReport()` → `useMutation({ mutationFn: apiClient.approveReport })` — provides `.mutate()`, `.isPending`
   - `useCaseAnalysis()` → `useMutation({ mutationFn: apiClient.analyzeCase })`
   - `useBackendStatus()` → `useQuery` on `apiClient.isBackendAvailable()`

5. **Fix `ChatAttachment` construction in [frontend/src/app/agent/page.tsx](frontend/src/app/agent/page.tsx)** — Replace `{ id, type, name, size }` with `{ id, type, name, url: URL.createObjectURL(file) }` to match the `ChatAttachment` type in [frontend/src/lib/types.ts](frontend/src/lib/types.ts)

### Phase 2: Patient Selector in Co-Pilot

6. **Create patient selector component** — New file `frontend/src/components/agent/PatientSelector.tsx`:
   - Dropdown/combobox that lists patients from `usePatients()` hook
   - Shows current patient name + MRN in the agent top bar
   - Search/filter within the dropdown
   - "Create New Patient" quick-add button at bottom
   - On selection, updates `useChatStore().setCurrentPatient(patient)`

7. **Refactor [frontend/src/app/agent/page.tsx](frontend/src/app/agent/page.tsx)** — Remove `mockPatient` dependency:
   - Replace hardcoded `mockPatient` with `useChatStore().currentPatient`
   - Add `PatientSelector` component at the top bar (replacing the hardcoded patient display)
   - In `handleSend()`, use `currentPatient.id` instead of `mockPatient.id`
   - Disable send button if no patient selected
   - Accept URL param `?patientId=` to pre-select a patient (enables linking from patients page)
   - Remove `mockChatMessages`/`mockCitations` from the "Load Demo" flow — replace with a demo prompt that triggers real API analysis

### Phase 3: Remove All Mock Fallbacks

8. **Clean [frontend/src/app/agent/page.tsx](frontend/src/app/agent/page.tsx)** — Remove mock simulation path:
   - Delete the `setTimeout` mock simulation that runs when backend is offline
   - If backend is offline, show a clear error state "Backend unavailable" instead of fake data
   - Remove "Load Demo" button entirely (or keep it but have it send a real analysis request with a pre-filled prompt)
   - Remove imports of `mockChatMessages`, `mockCitations`, `mockPatient` from `@/lib/mock-data`

9. **Clean [frontend/src/app/case/[id]/page.tsx](frontend/src/app/case/%5Bid%5D/page.tsx)** — Remove mock fallbacks:
   - Remove `mockReport`, `mockFindings`, `mockReasoningSteps`, `mockPatient` imports
   - If report fetch fails → show error state, not mock data
   - Use `mapApiResponseToAIReport()`, `mapApiFinding()`, `mapApiReasoningTrace()`, `mapApiPatient()` for real data transformation

10. **Clean [frontend/src/app/timeline/[patientId]/page.tsx](frontend/src/app/timeline/%5BpatientId%5D/page.tsx)** — Remove mock fallbacks:
    - Remove `mockPatient`, `mockTimelineEvents` imports
    - If timeline fetch fails → show error state with retry button
    - Use `mapApiTimelineEvent()`, `mapApiPatient()` for data transformation

11. **Delete [frontend/src/lib/api.ts](frontend/src/lib/api.ts)** — dead code, duplicate of `api/client.ts`

12. **Clean [frontend/src/lib/mock-data.ts](frontend/src/lib/mock-data.ts)** — After all pages stop importing it, either delete the file or keep only for unit tests (rename to `__tests__/mock-data.ts`)

### Phase 4: Fix Navigation & Routing

13. **Fix [frontend/src/components/layout/Navbar.tsx](frontend/src/components/layout/Navbar.tsx)**:
    - Remove hardcoded `"/case/demo"` link — instead link to `/patients` (cases are accessed per-patient)
    - Remove hardcoded `"/timeline/PT-12345"` link — instead link to `/patients` with note that timeline is accessed per-patient
    - Or: show most recent patient's timeline if user has a current patient context
    - Fix `DEFAULTS.authMode` reference — remove or add to constants

14. **Add "Start Co-Pilot" action from patients page**:
    - In [frontend/src/app/patients/page.tsx](frontend/src/app/patients/page.tsx), add a button/link on each patient row that navigates to `/agent?patientId={id}`
    - This allows doctors to select a patient and immediately open the co-pilot with that patient's context

15. **Add reports listing per patient**:
    - In [frontend/src/app/timeline/[patientId]/page.tsx](frontend/src/app/timeline/%5BpatientId%5D/page.tsx) or the patient detail area, show past AI reports for the patient using `apiClient.getPatientReports(patientId)` (already implemented in API client, never called)
    - Each report links to `/case/{reportId}` for full detail view

### Phase 5: Complete Patient CRUD

16. **Ensure patient creation works** — The modal form in [frontend/src/app/patients/page.tsx](frontend/src/app/patients/page.tsx) calls `useCreatePatient().mutate()`. After creating the `useCreatePatient` hook in step 4, verify the form fields match `ApiCreatePatientRequest` (`name`, `date_of_birth`, `gender`, `medical_record_number?`). Add query invalidation to refresh the list.

17. **Add patient edit capability** (backend needs new endpoint):
    - **Backend**: Add `PUT /api/v1/patients/{patient_id}` route in [backend/src/medai/api/routes/patients.py](backend/src/medai/api/routes/patients.py)
    - **Backend**: Add `update()` method to `BasePatientRepository` interface and `SqlAlchemyPatientRepository`
    - **Backend**: Add `PatientUpdateRequest` schema in [backend/src/medai/domain/schemas.py](backend/src/medai/domain/schemas.py)
    - **Frontend**: Add edit modal/form on the patients page (inline edit or separate modal)

### Phase 6: Enrich Seed Data

18. **Enhance seed data in [backend/src/medai/repositories/seed.py](backend/src/medai/repositories/seed.py)**:
    - Current 3 patients already have rich timelines (23 events). Verify all events have enough detail for the AI history search to find relevant context
    - Add a few more timeline events with imaging references, lab results, and medication changes to make the AI agent's history search more useful
    - Ensure `patient_history_text` can be assembled from timeline events for clinical context
    - Add a 4th patient for variety (e.g., cardiology case with ECG + echo + stress test history)

### Phase 7: Backend Fixes

19. **Fix `edits` field in report approval** — In [backend/src/medai/api/routes/cases.py](backend/src/medai/api/routes/cases.py) and `SqlAlchemyReportRepository.update_approval()`, actually apply edits from `ReportApprovalRequest.edits` to the report (e.g., allow editing diagnosis, plan, findings)

20. **Verify CORS configuration** — Ensure [backend/src/medai/main.py](backend/src/medai/main.py) `ALLOWED_ORIGINS` includes `http://localhost:3000` and that preflight requests work for auth-protected endpoints

21. **Verify `debug=false` mode works end-to-end** — With Modal endpoints deployed:
    - Confirm `HttpImageAnalysisTool` can reach MedGemma 4B at the configured endpoint
    - Confirm `HttpTextReasoningTool` can reach MedGemma 27B
    - Confirm `HttpHistorySearchTool` can reach the `/search` endpoint on MedGemma 27B
    - Confirm `HttpAudioAnalysisTool` can reach HeAR
    - If any endpoint is down, the error should be surfaced clearly (not swallowed)

### Phase 8: Integration Testing

22. **Start services locally**:
    - PostgreSQL via Docker: `docker compose up -d db`
    - Run migrations: `cd backend && alembic upgrade head`
    - Re-seed DB: `python -m medai.cli.seed`
    - Start backend: `cd backend && python -m uvicorn medai.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src`
    - Start frontend: `cd frontend && npm run dev`

23. **Test complete doctor workflow**:
    - Login as `doctor@medai.com / doctor123`
    - Navigate to Patients → verify 3+ seeded patients appear
    - Create a new patient → verify it persists and appears in list
    - Click "Start Co-Pilot" on a patient → verify agent page opens with correct patient context
    - Change patient in co-pilot → verify patient selector works
    - Type a clinical query (e.g., "Review this patient's respiratory history and recommend next steps") → verify real API call to `/cases/analyze`
    - Wait for AI response → verify tool execution, findings, diagnosis
    - Click "View Report" → navigate to case page with real data (no mock fallback)
    - Approve the report → verify approval persists
    - Go to patient timeline → verify AI report event appears
    - Login as admin → verify admin dashboard shows correct stats

**Verification**
- `npm run build` in frontend must succeed with zero errors
- All 33 backend tests must pass (`cd backend && python -m pytest`)
- `curl` tests: login → list patients → analyze case → get report → approve → verify state
- Browser test: full workflow from login through AI analysis to approval
- No mock data visible anywhere in the pages (all real API data)

**Decisions**
- Hooks rewritten to use React Query (TanStack) since it's already installed and pages expect its API shape (`.isLoading`, `.mutate()`, `.isPending`)
- Mock patient/data removed entirely — agent page has a patient selector, no fallback to fake data
- Patient edit endpoint added to backend (currently only create exists)
- Legacy `src/lib/api.ts` deleted — all API calls go through `src/lib/api/client.ts`
- `@/lib/store` implemented with Zustand (already in `package.json`) for agent page state management
- NavBar links made dynamic (no hardcoded patient IDs)
