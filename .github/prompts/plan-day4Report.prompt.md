# Day 4 Report — Agentic MedAI (AgentForge Hackathon)
**Date**: February 8, 2026 · **Deadline**: Feb 9 @ 12:00 (~15 hours)

---

## What We Built Today (Backend)

### The Full Agentic Pipeline Is Live — Real Models, Real Inference, E2E

We went from "unit tests pass with mocks" → **fully working agentic medical AI pipeline hitting real GPU models, returning structured clinical reports with doctor approval workflow**.

#### Architecture (proven working in production)

```
Doctor Query + Patient Data
        │
        ▼
┌─────────────────────────────────┐
│  Claude Orchestrator (Sonnet)   │  ← Anthropic tool-use API
│  Route → Dispatch → Collect     │
└──┬─────┬──────┬──────┬─────────┘
   │     │      │      │
   ▼     ▼      ▼      ▼
 IMAGE  TEXT   AUDIO  HISTORY     ← 4 specialist tools (parallel)
 (4B)  (27B)  (HeAR)  (Local)
   │     │      │      │
   └─────┴──────┴──────┘
        │
        ▼
  Judge Agent (Claude)
  Consensus / Conflict → re-query loop (max 2 cycles)
        │
        ▼
  FinalReport → Doctor Approves/Edits/Rejects
```

#### What We Shipped

1. **3 MedGemma models deployed on Modal GPUs** (15-min scaledown window)
   - MedGemma 4B IT (A10G) — multimodal image+text
   - MedGemma 27B Text IT (A100-80GB, bf16) — clinical reasoning
   - HeAR (T4) — health audio embeddings

2. **Full agentic loop** in `orchestrator.py`:
   - Claude picks tools based on case data → parallel dispatch via `asyncio.gather()` → results fed back → synthesis → judge evaluates consensus → re-query on conflict

3. **E2E test passed all 8 steps** (real Claude + real Modal):
   Health → Patients → Create → **Full Case Analysis (177.8s)** → Retrieve → Approve → Reports → Timeline

4. **Integration bugs fixed** (5 E2E runs to debug):
   - Created `LocalHistorySearchTool` (replaces broken HTTP history search)
   - Fixed Modal path routing, 303 redirect handling, parallel execution
   - Fixed `_synthesis` str crash in judge + orchestrator
   - Fixed judge markdown fence stripping

5. **108 tests** passing in ~5s

#### Real E2E Output

| Field | Value |
|-------|-------|
| **Diagnosis** | CAP, likely bacterial, superimposed on acute COPD exacerbation |
| **Confidence** | 0.85 |
| **Findings** | 3 (infiltrates, cardiomegaly, pulmonary edema) |
| **Reasoning** | 13-step chain |
| **Plan** | 9 items (antibiotics considering allergy, O₂, COPD mgmt, cessation) |

---

## Honest Assessment

### ✅ Real & Trustworthy
- Claude genuinely picks tools based on case data (agentic routing)
- Parallel tool dispatch + aggregation
- MedGemma 27B reasoning chain — genuine 13-step clinical analysis
- Judge evaluator-optimizer pattern with re-query loop
- Doctor-in-the-loop approval workflow

### ⚠️ Not Real (Identified Today)
- **Confidence scores** — model self-reported text, NOT calibrated probabilities
- **Bounding boxes** — LLM-hallucinated coordinates, NOT object detection → **deleting these**
- **HeAR classifier** — heuristic on norms, not fine-tuned
- **History search** — keyword overlap, not embedding-based RAG

---

## Tomorrow's Plan (Feb 9 — Submission Day)

**Mentor's guidance**: *"Більше технічну частину допиляти з агентами, їх оркестрацією та пайплайном — за неї багато балів дають"*

**Scoring**: Technical Concept = **50%** (Architecture 20%, Maturity 20%, Scalability 10%)

### 🔴 Priority 1: Structured Outputs — Kill JSON Fragility
**Problem**: Judge uses free-text JSON prompting → E2E showed parse failures.  
**Solution**: Anthropic has `output_config.format` with `type: "json_schema"` — **guaranteed valid JSON via constrained decoding**. Also `strict: true` on tool definitions.  
- Add `output_config={"format": {"type": "json_schema", "schema": JudgmentResult_schema}}` to judge `messages.create()`
- Add `strict: true` + `additionalProperties: false` to all tool definitions
- Use `client.messages.parse()` with Pydantic models → zero manual JSON parsing
- This is a **major technical maturity signal** for evaluators

### 🔴 Priority 2: Real Confidence from Model Logprobs
**Problem**: "confidence: 0.85" is text generation, not math.  
**Solution**: HuggingFace `.generate(return_dict_in_generate=True, output_scores=True)` → per-token log-probs → sequence-level confidence via mean/min token probability.  
- Update both Modal deploy scripts (4B + 27B) to return `logprob_confidence` alongside findings
- Label clearly: "Model Sequence Probability" not "Clinical Certainty"
- Doctors see honest, computed metrics

### 🟡 Priority 3: Rich Demo Data — Sell the Story
**Problem**: Seed data is minimal, history_search finds nothing for new patients.  
**Solution**: 2-3 detailed patients with multi-visit timelines (labs, imaging, encounters).  
- Pre-populate timeline events that history_search actually finds and references
- Use real public chest X-ray images for the demo
- Show the pipeline finding and reasoning about *prior visits*

### 🟡 Priority 4: RAG for Evidence Citations
**Problem**: History search is keyword-based. Evidence citations are empty.  
**Solution**: Lightweight vector store (ChromaDB/FAISS in-memory).  
- Embed timeline events at ingestion (sentence-transformers or MedGemma)
- Cosine similarity search in `LocalHistorySearchTool`
- Citations link to real retrieved docs with source + date

### 🟢 Priority 5: Polish Orchestration for Demo
- Structured logging showing ROUTE → DISPATCH → COLLECT → JUDGE → REPORT phases
- Timing breakdowns per tool call
- Test case showing judge re-query cycle (conflicting findings)
- E2E output is demo-ready (screen-recordable as-is)

### 🟢 Priority 6: Remove Bboxes, Clean Image Output
- Remove `region_bbox` from 4B prompt (stop asking model to hallucinate)
- Keep field as Optional in entity (future MedSigLIP/MedSAM)
- Delete annotated image artifacts

### If Time Permits (v2)
- MedSigLIP attention maps (real spatial grounding)
- MedSAM3 segmentation (precise localization)
- Extended Thinking for deeper orchestrator reasoning
- Frontend ↔ backend integration
- FHIR/Anthropic healthcare connectors

---

## File Inventory

```
backend/src/medai/
├── domain/         entities.py (19 entities), interfaces.py (7 ABCs), schemas.py (12 schemas)
├── services/       orchestrator.py, judge.py, tool_registry.py
├── tools/          http.py (4 HTTP tools), local.py (history search), mock.py (4 mocks)
├── api/            dependencies.py (DI), routes/ (cases, patients, health)
├── repositories/   In-memory (patients, reports, timeline) + seed data
└── config.py

deploy/modal/       medgemma_4b.py, medgemma_27b.py, hear_audio.py, deploy_all.py

tests/              108 tests (6 unit, 2 integration, 1 E2E) + fixtures + report output
```

**Numbers**: 108 tests · 3 GPU models · 177.8s pipeline · $2.70 Modal spend · ~15h to deadline
