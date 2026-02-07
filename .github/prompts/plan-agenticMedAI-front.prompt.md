# End-to-End Agentic MedAI System — Master Plan

## Mission Statement

Build an **end-to-end agentic medical AI assistant for doctors** (not patients) that leverages Google's MedGemma model family (text, image, audio) orchestrated by Anthropic Claude. The core differentiator is **radical explainability** — every AI output must be traceable and understandable. The system includes a **longitudinal health timeline** (patient history across years) and a **multi-agent consensus mechanism** (judgment cycles). The team is 3 people, budget-constrained ($100 Anthropic API), targeting a working MVP/POC.

> **Vision**: Eliminate medical 'dark data' and ensure no diagnosis is ever missed due to human fatigue or fragmented records. A patient's history from 2015 should actively inform a prescription in 2026.

> **User**: The DOCTOR, not the patient. Process is DOCTOR first → AI second.

---

## Problem Statement

Doctors face a "cognitive overload" crisis: the expectation to process extensive patient history, numerous lab values, and ever-growing medical literature under severe time constraints results in information gaps and diagnostic errors. Our Agentic Product addresses the gap between vast available data and limited reading time.

**Business Objectives:**

- Reduce documentation time from 12 minutes to 2 minutes per patient
- Increase first-visit diagnostic accuracy by 15% via agentic cross-referencing
- NO integration to other platforms so far

**Target Users:**

| Tier | User | Value Proposition |
|------|------|-------------------|
| Primary | Overburdened GPs in public sector (Helsi/eHealth) | Cognitive offload, faster documentation |
| Secondary | Hospital administrators, private clinic owners | Lower malpractice costs, higher throughput |
| Tertiary | Patients | Enhanced "second opinion" support layer |

---

## Architecture Overview

```
Patient Data Inflow (Images, Text, Labs, Audio)
                    │
                    ▼
┌──────────────────────────────────────────────────────┐
│          ORCHESTRATOR — Claude Sonnet 3.5            │
│   (Anthropic API · Tool-Use · Routing · Planning)    │
│   Receives doctor query + patient context            │
│   Plans subtasks · Dispatches to specialist tools    │
│   Aggregates results · Runs judgment cycle           │
└──────┬──────────┬──────────┬──────────┬──────────────┘
       │          │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌──▼─────┐ ┌──▼──────┐
  │ IMAGE  │ │  TEXT   │ │ AUDIO  │ │HISTORY  │
  │ TOOL   │ │  TOOL   │ │ TOOL   │ │ TOOL    │
  │MedGemma│ │MedGemma│ │ HeAR + │ │RAG over │
  │4B IT + │ │27B Text│ │MedGemma│ │Patient  │
  │SigLIP  │ │  IT    │ │  4B    │ │Timeline │
  └────┬───┘ └───┬────┘ └──┬─────┘ └──┬──────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
  Structured JSON: findings, confidence, explanations,
  highlighted regions, cited evidence, embeddings
       │          │          │          │
       └──────────┴──────────┴──────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   JUDGE AGENT (Claude)│
        │  Consensus check      │
        │  Conflict detection   │
        │  Re-query if needed   │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  FINAL STRUCTURED     │
        │  REPORT (JSON/MD)     │
        │  + Explainability     │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  DOCTOR DASHBOARD     │
        │  (Next.js Web App)    │
        │  Timeline · Reports   │
        │  Image overlays       │
        │  Approve / Edit       │
        └───────────────────────┘
```

### Agentic Patterns Used (per Anthropic Best Practices)

| Pattern | Application in Our System |
|---------|--------------------------|
| **Routing** | Classify doctor query → dispatch to relevant specialist tools (image/text/audio/history) |
| **Parallelization + Voting** | Run multiple specialist analyses simultaneously, aggregate for consensus |
| **Evaluator-Optimizer** | Judge Agent validates outputs, re-queries on conflict (max 2 cycles) |
| **Orchestrator-Workers** | Claude plans dynamically, delegates to MedGemma-powered tools |
| **Human-in-the-loop** | Doctor approves/edits/rejects every AI output before it becomes part of the record |

> **Design Principle (Anthropic):** "The most successful implementations use simple, composable patterns rather than complex frameworks."

---

## Model Inventory & Capabilities

### Available Models from Google Health AI Developer Foundations

| Model | Type | Size | Modalities | Primary Use | Our Role |
|-------|------|------|-----------|-------------|----------|
| **MedGemma 4B IT** | Multimodal VLM | 4B params | Text + Images → Text | Medical image interpretation, clinical reasoning | **Image Analysis Tool** |
| **MedGemma 27B Text IT** | Text-only LLM | 27B params | Text → Text | Medical text reasoning, EHR analysis | **Text Reasoning Tool** |
| **MedGemma 27B IT** | Multimodal VLM | 27B params | Text + Images + EHR → Text | Combined analysis, FHIR records | Future upgrade path |
| **MedSigLIP** | Image encoder | 400M+400M | Images + Text → Embeddings | Zero-shot classification, image retrieval | **Image Triage + Explainability (attention maps)** |
| **HeAR** | Audio encoder | ViT-L (~300M) | Audio → Embeddings (512-dim) | Cough/breathing analysis | **Audio Analysis Tool** |
| **Path Foundation** | Histopathology encoder | — | Images → Embeddings | Histopathology classification | Future: pathology module |

### Key Performance Benchmarks

**Text (MedGemma 27B Text IT):**

| Benchmark | MedGemma 27B | Base Gemma 3 27B | GPT-4o |
|-----------|-------------|-----------------|--------|
| MedQA (4-op, 0-shot) | **87.7** | 74.9 | 86.5 |
| MedMCQA | **74.2** | 62.6 | 76.1 |
| MMLU Med (avg) | **87.0** | 83.3 | ~89 |
| AgentClinic-MedQA | **56.2%** | — | 65.8% (o3) |
| vs Human Physician | **56.2%** | — | 54.0% (human) |

**Image (MedGemma 4B IT):**

| Benchmark | MedGemma 4B | Gemma 3 4B base |
|-----------|------------|----------------|
| MIMIC-CXR top-5 conditions | **88.9** macro F1 | 81.2 |
| PathMCQA (histopathology) | **69.8%** | 37.1% |
| EyePACS (ophthalmology) | **64.9%** | 14.4% |

**Critical Notes:**

- ⚠️ MedGemma 4B "had difficulty following system instructions for agentic framework" — use as **tool only**, not as agent
- ✅ MedGemma 27B outperforms human physicians on AgentClinic — suitable for agentic reasoning
- ✅ Fine-tuned 27B achieves 93.6% on FHIR-based EHR QA
- ✅ 500× less compute cost than largest comparator models while remaining competitive

### GPU/RAM Requirements

| Model | Min GPU | VRAM Needed | Quantized? | Est. Modal Cost |
|-------|---------|-------------|-----------|----------------|
| MedGemma 4B IT | 1× A10 (24GB) | ~8-10GB (bf16) | 42 variants available | ~$1.10/hr |
| MedGemma 27B Text IT | 1× A100 80GB | ~54GB (bf16) | 25 variants (Q4 fits A100 40GB) | ~$2.10-3.95/hr |
| MedSigLIP | CPU or T4 | ~1.6GB | Not needed | ~$0.59/hr |
| HeAR | CPU | ~1GB | Not needed | ~$0.00 (CPU) |

---

## Specialist Tool Design

### Tool 1: Image Analysis (MedGemma 4B IT + MedSigLIP)

**Input:** Medical image (DICOM/PNG/JPEG) + doctor's question/context
**Processing Pipeline:**

```
Image Upload
    │
    ├──→ MedSigLIP (fast triage)
    │      → Zero-shot classification
    │      → Attention map extraction (explainability heatmap)
    │      → Embedding for history search
    │
    └──→ MedGemma 4B IT (deep analysis)
           → Structured findings with confidence scores
           → Chain-of-thought explanation
           → Abnormality descriptions
```

**Output Schema:**

```json
{
  "tool": "image_analysis",
  "modality_detected": "chest_xray",
  "findings": [
    {
      "finding": "Right lower lobe consolidation",
      "confidence": 0.89,
      "explanation": "Dense opacity in the right lower zone with air bronchograms, consistent with pneumonia",
      "region_bbox": [120, 340, 280, 480],
      "severity": "moderate"
    }
  ],
  "attention_heatmap_url": "/api/v1/artifacts/{id}/heatmap.png",
  "embedding_vector": "stored_in_vector_db",
  "differential_diagnoses": ["pneumonia", "atelectasis", "pleural_effusion"],
  "recommended_followup": ["lateral CXR", "CBC with differential", "sputum culture"]
}
```

### Tool 2: Text Reasoning (MedGemma 27B Text IT)

**Input:** Patient history text, lab results, clinical question
**Processing:** Chain-of-thought medical reasoning with test-time scaling

**Output Schema:**

```json
{
  "tool": "text_reasoning",
  "reasoning_chain": [
    {"step": 1, "thought": "Patient presents with 3-day history of productive cough..."},
    {"step": 2, "thought": "Lab values show elevated WBC (14.2k) and CRP (45mg/L)..."},
    {"step": 3, "thought": "Given imaging findings from image_analysis tool showing RLL consolidation..."}
  ],
  "assessment": "Community-acquired pneumonia, likely bacterial",
  "confidence": 0.85,
  "evidence_citations": [
    {"source": "patient_history_2024-03-15", "relevant_excerpt": "..."},
    {"source": "lab_result_2026-02-07", "relevant_excerpt": "..."}
  ],
  "plan_suggestions": ["Amoxicillin-clavulanate 875/125mg BID x 7 days", "Follow-up CXR in 6 weeks"],
  "contraindication_check": {"flagged": false, "details": null}
}
```

### Tool 3: Audio Analysis (HeAR + downstream classifier)

**Input:** Audio recording (cough, breathing, lung sounds) — 16kHz mono
**Processing:**

```
Audio File
    │
    ├──→ Segment into 2-second windows
    ├──→ HeAR encoder → 512-dim embeddings per window
    ├──→ Lightweight classifier head (trained on cough/wheeze/crackle datasets)
    └──→ Temporal analysis (which segments are abnormal)
```

**Output Schema:**

```json
{
  "tool": "audio_analysis",
  "audio_type": "breathing",
  "segments": [
    {"time_start": 0.0, "time_end": 2.0, "classification": "normal", "confidence": 0.92},
    {"time_start": 2.0, "time_end": 4.0, "classification": "wheeze", "confidence": 0.78},
    {"time_start": 4.0, "time_end": 6.0, "classification": "crackle", "confidence": 0.65}
  ],
  "summary": "Intermittent wheezing and crackles detected in mid-segments",
  "abnormal_segment_timestamps": [2.0, 4.0],
  "embedding_vector": "stored_in_vector_db"
}
```

### Tool 4: Patient History / Timeline (RAG over Vector DB)

**Input:** Patient ID + query context (current findings, question)
**Processing:** Semantic search over patient's historical embeddings (MedSigLIP image embeddings + HeAR audio embeddings + text embeddings)

**Output Schema:**

```json
{
  "tool": "history_search",
  "patient_id": "PT-12345",
  "relevant_records": [
    {
      "date": "2024-03-15",
      "type": "imaging",
      "summary": "Previous CXR showed clear lung fields",
      "similarity_score": 0.87,
      "clinical_relevance": "Comparison baseline — new consolidation is acute change"
    },
    {
      "date": "2023-11-20",
      "type": "lab",
      "summary": "Baseline WBC 7.2k, CRP <5",
      "similarity_score": 0.72,
      "clinical_relevance": "Current elevation represents significant change from baseline"
    }
  ],
  "timeline_context": "Patient has no prior history of pneumonia. Last imaging 11 months ago was normal."
}
```

---

## Judgment Cycle (Consensus Mechanism)

```
         Specialist Tool Results (all JSON)
                    │
                    ▼
    ┌───────────────────────────────┐
    │      JUDGE PROMPT (Claude)    │
    │                               │
    │  "Given these specialist      │
    │   findings, check for:        │
    │   1. Contradictions           │
    │   2. Low-confidence items     │
    │   3. Missing context          │
    │   4. Guideline compliance     │
    │                               │
    │  Return: CONSENSUS or         │
    │          CONFLICT + re-query" │
    └──────────────┬────────────────┘
                   │
          ┌────────┴────────┐
          │                 │
     CONSENSUS         CONFLICT
          │                 │
          ▼                 ▼
   Final Report      Re-dispatch to
   Generated         specific tools
                     with additional
                     context (max 2×)
                          │
                          ▼
                    Back to Judge
```

**Judgment Criteria:**

1. **Cross-modal consistency**: Do image findings align with text reasoning?
2. **Confidence thresholds**: Any finding below 0.6 confidence triggers re-analysis
3. **Historical consistency**: Do current findings make sense given patient timeline?
4. **Guideline adherence**: Does the suggested plan follow clinical guidelines?

**Budget protection**: Hard cap at 2 re-query cycles per case (~3 Claude calls total: orchestrate + judge + optional re-judge)

---

## Data Architecture

### Storage Layer

```
┌─────────────────────────────────────────────────────┐
│                   DATA LAYER                         │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  PostgreSQL   │  │  Vector DB   │  │  Object    │ │
│  │  (Supabase)   │  │  (Qdrant)    │  │  Storage   │ │
│  │               │  │              │  │  (R2/Modal)│ │
│  │ • Patients    │  │ • MedSigLIP  │  │            │ │
│  │ • Encounters  │  │   image emb. │  │ • DICOM    │ │
│  │ • Lab Results │  │ • HeAR audio │  │ • Images   │ │
│  │ • Reports     │  │   embeddings │  │ • Audio    │ │
│  │ • Timeline    │  │ • Text emb.  │  │ • Reports  │ │
│  │   Events      │  │   (all 512d) │  │   (PDF)    │ │
│  │ • AI Outputs  │  │              │  │            │ │
│  │   (audit log) │  │              │  │            │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────┘
```

### FHIR-Compatible Schema (Simplified for MVP)

```sql
-- Core entities (FHIR-inspired, simplified)
patients (id, name, dob, gender, medical_record_number)
encounters (id, patient_id, date, type, chief_complaint, status)
observations (id, encounter_id, type, value, unit, reference_range, timestamp)
imaging_studies (id, encounter_id, modality, body_site, storage_url, siglip_embedding_id)
audio_recordings (id, encounter_id, type, storage_url, hear_embedding_id)
ai_reports (id, encounter_id, orchestrator_trace, specialist_outputs_json, judge_verdict, final_report_json, doctor_approval_status)
timeline_events (id, patient_id, date, event_type, summary, source_id, source_type)
```

### Test Dataset: UW-Madison GI Tract

- **Why**: Multi-day temporal scans per patient — ideal for timeline feature validation
- **Structure**: `train/<case>/<case_day>/<scans>/` with 16-bit grayscale PNGs
- **Size**: 2.47 GB, 38,496 files, ~50 cases with multiple timepoints
- **Metadata**: Pixel spacing in mm, 3mm slice thickness
- **Masks**: RLE-encoded segmentation (stomach, large bowel, small bowel)
- **Usage**: Load cases as "patients," each scan day as a "timeline event," demonstrate longitudinal tracking

---

## Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Orchestrator** | Anthropic Claude 3.5 Sonnet (tool-use) | Provided API, best agentic performance, cost-efficient |
| **Image Analysis** | MedGemma 4B IT + MedSigLIP | Multimodal, 88.9 F1 on CXR, attention maps for explainability |
| **Text Reasoning** | MedGemma 27B Text IT (quantized Q4) | 87.7% MedQA, outperforms human physicians on AgentClinic |
| **Audio Analysis** | HeAR (google/hear-pytorch) | 512-dim embeddings, cough/breathing, 313M training clips |
| **Model Hosting** | Modal (serverless GPU) | Pay-per-second, $30 free tier, scale-to-zero, fastest setup |
| **Backend API** | FastAPI (Python) | Async, Pydantic schemas match structured outputs, OpenAPI docs |
| **Frontend** | Next.js 14 + Tailwind + shadcn/ui | Fast iteration, Vercel free hosting, rich component ecosystem |
| **Vector DB** | Qdrant (or ChromaDB for simplicity) | Semantic search over patient history embeddings |
| **Database** | PostgreSQL (Supabase free tier) | FHIR-compatible records, proven, free hosting |
| **Object Storage** | Modal Volumes or Cloudflare R2 | Medical images/audio, cost-effective |
| **Framework** | Raw Anthropic SDK (no LangGraph/CrewAI) | Per Anthropic's advice: simple composable patterns > frameworks |

### Why NOT LangGraph/CrewAI?

Per Anthropic's own guidance: "The most successful implementations use simple, composable patterns rather than complex frameworks." For a 3-person team on a tight timeline:

- Raw Anthropic SDK = full control, zero learning curve, transparent for demo
- LangGraph = additional abstraction layer, overkill for a single orchestrator pattern
- CrewAI = even more abstraction, magic that's hard to debug under time pressure

We implement our own lightweight state machine: `ROUTE → DISPATCH → COLLECT → JUDGE → OUTPUT`

---

## Hosting & Cost Analysis

### Modal Serverless GPU (Recommended for MVP)

| Component | GPU | Est. Cost/hr | Monthly (8hr/day) |
|-----------|-----|-------------|-------------------|
| MedGemma 4B IT | A10 (24GB) | $1.10 | ~$264 |
| MedGemma 27B Text IT (Q4) | A100 40GB | $2.10 | ~$504 |
| MedSigLIP | T4 (16GB) | $0.59 | ~$142 |
| HeAR | CPU | ~$0.00 | ~$0 |

**With serverless scale-to-zero (realistic hackathon usage):**

| Component | Est. Active Hours | Est. Total Cost |
|-----------|------------------|----------------|
| MedGemma 4B | ~10 hrs total | ~$11 |
| MedGemma 27B (Q4) | ~10 hrs total | ~$21 |
| MedSigLIP | ~5 hrs total | ~$3 |
| HeAR | ~2 hrs total | ~$0 |
| **Total hackathon** | | **~$35** |

**Modal free tier**: $30/month. Startup credits up to $25k available.

### Alternative: Kaggle/Colab for Development

- **Kaggle**: Free T4/P100 (30 hrs/week) — good for model experimentation
- **Colab Pro**: $10/mo for A100 access — good for 27B model testing
- **Use for**: Development, testing, fine-tuning
- **Don't use for**: Production serving (no API endpoint capability)

### Anthropic API Budget ($100)

| Model | Input Cost | Output Cost | Est. per Case |
|-------|-----------|-------------|--------------|
| Claude 3.5 Sonnet | $3/M tokens | $15/M tokens | ~$0.02-0.05 |
| With prompt caching | $0.30/M cached | $15/M output | ~$0.01-0.03 |

**Budget allows**: ~2,000-5,000 full case analyses
**Strategy**: Never send images to Claude (only structured JSON), use prompt caching for system prompts

---

## End-to-End Interaction Flow

### Example: Doctor Uploads Chest X-Ray + Patient History

```
STEP 1: Doctor opens patient profile, uploads new CXR image
        Types: "New chest X-ray for follow-up. Patient complaining of persistent cough x 3 weeks."

STEP 2: Frontend sends to Backend API:
        POST /api/v1/cases/analyze
        {
          "patient_id": "PT-12345",
          "image_urls": ["s3://bucket/cxr-20260207.dcm"],
          "clinical_context": "Persistent cough x 3 weeks, follow-up",
          "doctor_query": "Assess for any pathology, compare with previous imaging"
        }

STEP 3: Backend → Claude Orchestrator (Tool-Use)
        Claude receives query + patient context
        Claude PLANS: "I need to run 3 tools in parallel:
          1. image_analysis(cxr image + context)
          2. history_search(patient PT-12345, query: previous imaging + respiratory)
          3. text_reasoning(clinical context + lab values from EHR)"

STEP 4: Backend executes all 3 tools in parallel:
        → MedGemma 4B: analyzes CXR → finds RLL consolidation (conf: 0.89)
        → MedSigLIP: generates attention heatmap → highlights RLL region
        → Qdrant: retrieves previous CXR from 2024-03-15 (clear lungs)
        → MedGemma 27B: reasons over patient history + lab values

STEP 5: All results → Claude Judge prompt
        Judge checks:
        ✅ Image finding (consolidation) aligns with text reasoning (elevated WBC/CRP)
        ✅ History shows this is NEW finding (previous CXR was clear)
        ✅ Confidence above threshold (0.89 > 0.6)
        ⚠️ Suggests comparing with lateral view if available
        → VERDICT: CONSENSUS

STEP 6: Claude generates Final Structured Report:
        {
          "diagnosis": "Community-acquired pneumonia (RLL)",
          "confidence": 0.87,
          "evidence_summary": "New RLL consolidation on CXR (not present 2024-03-15)...",
          "timeline_impact": "First respiratory event in patient history",
          "plan": ["Antibiotics", "Follow-up CXR 6 weeks", "Consider sputum culture"],
          "explainability": {
            "heatmap_url": "/artifacts/heatmap-cxr-20260207.png",
            "reasoning_trace": [...],
            "historical_comparison": {...}
          }
        }

STEP 7: Frontend renders:
        ┌────────────────────────────────────────────┐
        │  Patient: John Doe (PT-12345)              │
        │  ─────────────────────────────────         │
        │  📊 TIMELINE                                │
        │  2023-11 ● Labs (baseline normal)          │
        │  2024-03 ● CXR (clear)                     │
        │  2026-02 ● CXR (NEW: RLL consolidation) ⚠️ │
        │                                            │
        │  🔬 AI ANALYSIS                             │
        │  [CXR Image] [Toggle Heatmap Overlay]      │
        │  Finding: RLL Consolidation (89% conf)     │
        │  Compared to: 2024-03-15 CXR (clear)      │
        │                                            │
        │  📋 REASONING TRACE                         │
        │  ▸ Step 1: Imaging analysis...             │
        │  ▸ Step 2: Lab correlation...              │
        │  ▸ Step 3: Historical comparison...        │
        │                                            │
        │  [✅ Approve] [✏️ Edit] [❌ Reject]         │
        └────────────────────────────────────────────┘

STEP 8: Doctor reviews, clicks [Approve] with optional edits
        → Report saved to ai_reports table
        → Timeline event created
        → Embeddings stored for future retrieval
```

---

## MVP Scope Definition

### In Scope (Must Have for POC)

| Feature | Description | Priority |
|---------|------------|----------|
| Image analysis | Upload CXR/GI image → get findings + heatmap | P0 |
| Text reasoning | Patient history → structured assessment | P0 |
| Claude orchestration | Tool-use routing + aggregation | P0 |
| Judgment cycle | Single consensus check (1 round) | P0 |
| Explainability | Attention heatmaps + reasoning traces | P0 |
| Patient timeline | Basic chronological view of events | P0 |
| Doctor dashboard | Single patient case view with approve/reject | P0 |
| Structured outputs | All tools return typed JSON | P0 |

### Nice to Have (If Time Allows)

| Feature | Description | Priority |
|---------|------------|----------|
| Audio analysis (HeAR) | Cough/breathing → findings | P1 |
| Multi-image comparison | Side-by-side current vs historical | P1 |
| Vector search over history | Semantic retrieval of similar past cases | P1 |
| Re-query loop (Judge conflict) | 2nd round of specialist queries on conflict | P1 |
| Report PDF export | Downloadable structured report | P2 |

### Out of Scope for MVP

- Real FHIR integration / HL7 interop
- Multi-patient dashboard / patient list
- Authentication / RBAC / audit logging
- Mobile responsive design
- Real-time streaming responses
- Fine-tuning MedGemma on custom data
- Production security / HIPAA compliance
- Integration with external EHR platforms

---

## Team Breakdown (3 People)

### Person A — Backend/ML Engineer

**Focus**: Model serving, Modal deployment, tool APIs, embeddings pipeline

| Task | Est. Time | Deliverable |
|------|----------|-------------|
| Set up Modal project + MedGemma 4B endpoint | 3-4 hrs | Working inference endpoint |
| Set up MedGemma 27B (quantized) endpoint | 3-4 hrs | Working text reasoning endpoint |
| Set up MedSigLIP endpoint + attention maps | 2-3 hrs | Embedding + heatmap endpoint |
| Build FastAPI gateway with tool schemas | 4-5 hrs | Unified API with OpenAPI docs |
| Set up Qdrant + embedding ingestion | 3-4 hrs | Vector search working |
| Integration testing all tools | 2-3 hrs | All endpoints returning valid JSON |
| **Total** | **~18-23 hrs** | |

### Person B — Agentic/Backend Engineer

**Focus**: Claude orchestrator, tool definitions, judgment cycle, data schema

| Task | Est. Time | Deliverable |
|------|----------|-------------|
| Design Claude tool schemas (JSON) | 2-3 hrs | Tool definitions for all 4 tools |
| Implement orchestrator (routing + dispatch) | 4-5 hrs | Working multi-tool orchestration |
| Implement judgment cycle | 3-4 hrs | Consensus/conflict detection |
| Set up PostgreSQL schema + Supabase | 2-3 hrs | Database with FHIR-lite schema |
| Load GI Tract test data as patients | 2-3 hrs | Sample patients with timeline data |
| Build case analysis API endpoint | 3-4 hrs | POST /api/v1/cases/analyze working end-to-end |
| Prompt engineering + testing | 3-4 hrs | Optimized prompts for all agents |
| **Total** | **~19-26 hrs** | |

### Person C — Frontend/Demo Engineer

**Focus**: Next.js dashboard, timeline UI, image viewer, demo preparation

| Task | Est. Time | Deliverable |
|------|----------|-------------|
| Next.js project setup + Tailwind + shadcn | 1-2 hrs | Boilerplate ready |
| Patient timeline component | 4-5 hrs | Interactive chronological timeline |
| Case analysis view (image + findings) | 4-5 hrs | Split view with findings panel |
| Heatmap overlay toggle on images | 3-4 hrs | Canvas-based overlay rendering |
| Reasoning trace collapsible display | 2-3 hrs | Step-by-step reasoning UI |
| Approve/Edit/Reject workflow | 2-3 hrs | Doctor interaction buttons |
| Polish + responsive + loading states | 2-3 hrs | Production-quality feel |
| Record demo video (5 min) | 2-3 hrs | Screen recording with narration |
| Pitch deck preparation | 2-3 hrs | Slides with architecture + demo |
| **Total** | **~22-31 hrs** | |

### Parallel Workstreams

```
Day 1:  A: Modal setup + MedGemma 4B    B: Claude tool schemas + DB     C: Next.js boilerplate + timeline
Day 2:  A: MedGemma 27B + SigLIP        B: Orchestrator + routing       C: Case view + image viewer
Day 3:  A: FastAPI gateway + Qdrant      B: Judgment cycle + prompts     C: Heatmap overlay + reasoning
Day 4:  A: Integration testing           B: End-to-end testing           C: Polish + demo prep
Day 5:  ALL: Bug fixes, demo recording, submission
```

---

## Competitive Landscape

| Solution | Approach | Our Differentiation |
|----------|---------|-------------------|
| Google Ambient AI | Clinical documentation | We focus on **diagnostic support**, not dictation |
| Microsoft DAX / Nuance | Ambient listening + notes | We provide **explainable multi-modal analysis** |
| Microsoft BioGPT | Text-only biomedical LLM (legacy) | We are **multimodal** (image + text + audio) + **agentic** |
| Rad-AI / Aidoc | Radiology-specific AI | We cover **multiple specialties** + **longitudinal timeline** |
| Epic/Oracle EHR AI | Embedded in EHR platforms | We are **platform-independent** + **open-source models** |

**Our Unique Value:**

1. **Radical Explainability** — heatmaps, reasoning traces, confidence scores, historical comparisons
2. **Longitudinal Timeline** — AI that remembers and cross-references across years of patient history
3. **Multi-Agent Consensus** — judgment cycles that catch contradictions before reaching the doctor
4. **Open-Source Models** — no vendor lock-in, fully auditable, customizable
5. **Doctor-First Design** — AI as assistant, not replacement; human approves everything

---

## Risk Assessment & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| Modal cold starts (30-60s for 27B) | Poor UX | High | `keep_warm=1` for demo, show loading animation |
| $100 Anthropic budget burned fast | System stops working | Medium | Hard cap 2 judgment cycles, prompt caching, monitor costs |
| MedGemma 4B poor structured output | Bad tool responses | Medium | Extensive prompt engineering, fallback parsing, validation |
| GradCAM/attention maps complex to extract | No heatmaps for demo | Medium | Start with MedSigLIP attention (simpler), fallback to bounding boxes |
| 27B model too large for budget | No text reasoning | Low | Use quantized (Q4 fits A100 40GB) or fall back to 4B for text |
| Integration complexity across 3 workstreams | Broken end-to-end | High | Define API contracts on Day 1, daily integration checkpoints |
| Demo data doesn't look compelling | Weak presentation | Medium | Pre-select best GI Tract cases, curate CXR examples with clear pathology |

---

## Open Questions for Team

1. **GPU access**: Do team members have personal GPUs, Colab Pro, or Kaggle accounts? This affects development speed.
2. **Frontend experience**: Is Person C comfortable with Next.js + Canvas API for heatmap overlays, or should we simplify to static image overlays?
3. **Primary demo dataset**: Confirm GI Tract (timeline) + sample CXRs (image analysis) as demo data.
4. **Anthropic model choice**: Claude 3.5 Sonnet (cheaper, faster) vs Claude 3 Opus (smarter, slower, 5× more expensive)?
5. **Audio scope**: Include HeAR in MVP or defer to post-hackathon?
6. **Quantization strategy for 27B**: GGUF Q4 vs AWQ vs GPTQ — need to test which runs best on Modal A100 40GB.

---

## References & Resources

- [MedGemma Collection (HuggingFace)](https://huggingface.co/collections/google/medgemma-release-680aff39dc03e81e269a3e1d)
- [MedGemma Concept Apps](https://huggingface.co/collections/google/medgemma-concept-apps-6848c411b4ea95e547753cbb)
- [Google Health AI Developer Foundations](https://developers.google.com/health-ai-developer-foundations)
- [HeAR Model](https://developers.google.com/health-ai-developer-foundations/hear)
- [UW-Madison GI Tract Dataset](https://www.kaggle.com/competitions/uw-madison-gi-tract-image-segmentation/data)
- [Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic Tool Use Docs](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Modal Docs](https://modal.com/docs/guide)
- [MedGemma Technical Report](./medgemma_technical_report.txt)
