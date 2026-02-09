# MedAI Mermaid Diagrams for Pitch Deck

---

## Diagram 1 — Core Agent Pipeline (Orchestrator-Workers + Judge)

This is the main diagram showing the full agentic cycle: doctor input → orchestrator → parallel tool dispatch → judge evaluation → report.

```mermaid
flowchart TD
    subgraph INPUT["👨‍⚕️ Doctor Input"]
        D1[Patient ID]
        D2[Clinical Query]
        D3[Medical Images<br/><i>X-ray, CT, MRI, etc.</i>]
        D4[Audio Recordings<br/><i>Breathing, Cough</i>]
        D5[Lab Results]
        D6[Clinical Context]
    end

    INPUT --> API["<b>FastAPI Backend</b><br/>POST /api/v1/cases/analyze/stream"]
    API --> ORCH

    subgraph ORCH["🧠 Phase 1 — ROUTING<br/><i>Claude Sonnet 4 (Anthropic API)</i>"]
        R1["Analyze case data"]
        R2["Select relevant tools<br/>based on routing rules"]
        R3["Generate parallel<br/>tool_use calls"]
        R1 --> R2 --> R3
    end

    ORCH -->|"Parallel Dispatch"| TOOLS

    subgraph TOOLS["⚙️ Phase 2 — PARALLEL TOOL EXECUTION"]
        direction TB

        subgraph T1["🔬 image_analysis"]
            T1M["<b>MedGemma 4B IT</b><br/><i>google/medgemma-4b-it</i><br/>Modal · A10G GPU"]
            T1O["Structured findings<br/>confidence scores<br/>severity levels<br/>differential diagnoses"]
            T1M --> T1O
        end

        subgraph T2["🧪 text_reasoning"]
            T2M["<b>MedGemma 27B Text IT</b><br/><i>google/medgemma-27b-text-it</i><br/>Modal · A100-80GB GPU"]
            T2O["Chain-of-thought assessment<br/>evidence citations<br/>treatment plan<br/>contraindication flags"]
            T2M --> T2O
        end

        subgraph T3["🎧 audio_analysis"]
            T3M["<b>HeAR</b><br/><i>google/hear-pytorch</i><br/>Modal · T4 GPU"]
            T3O["Segment classification<br/>normal / wheeze /<br/>crackle / abnormal"]
            T3M --> T3O
        end

        subgraph T4["📋 history_search"]
            T4M["<b>TF-IDF RAG Engine</b><br/><i>Local · PostgreSQL</i>"]
            T4O["Ranked prior records<br/>prior AI report summaries<br/>timeline context"]
            T4M --> T4O
        end

        subgraph T5["🔥 image_explainability"]
            T5M["<b>MedSigLIP</b><br/><i>google/medsiglip-448</i><br/>Modal · T4 GPU"]
            T5O["Per-condition sigmoid scores<br/>32×32 spatial heatmaps<br/>11-modality taxonomy"]
            T5M --> T5O
        end
    end

    TOOLS --> COLLECT["Phase 3 — COLLECT & SYNTHESIZE<br/><i>Claude Sonnet 4</i><br/>Aggregate all tool results<br/>Generate brief diagnosis"]

    COLLECT --> JUDGE

    subgraph JUDGE["⚖️ Phase 4 — JUDGE EVALUATION<br/><i>Claude Sonnet 4 · Structured Outputs</i>"]
        J1["Evaluate cross-modal consistency"]
        J2["Check confidence levels<br/><i>threshold: 0.6</i>"]
        J3["Verify historical consistency"]
        J4["Assess guideline adherence"]
        J1 --> J5
        J2 --> J5
        J3 --> J5
        J4 --> J5
        J5{"Verdict?"}
    end

    J5 -->|"✅ CONSENSUS"| REPORT
    J5 -->|"❌ CONFLICT"| REQUERY["Re-query failed tools<br/><i>max 2 cycles</i>"]
    REQUERY -->|"Only failed tools"| TOOLS

    subgraph REPORT["📄 Phase 5 — REPORT GENERATION"]
        RP1["Aggregate findings &<br/>reasoning traces"]
        RP2["Extract heatmap PNGs<br/>from SigLIP"]
        RP3["Save to PostgreSQL<br/>+ JSON artifacts"]
        RP4["Create timeline event<br/>for patient"]
        RP1 --> RP2 --> RP3 --> RP4
    end

    REPORT --> REVIEW

    subgraph REVIEW["👨‍⚕️ Human-in-the-Loop"]
        RV1["Doctor reviews<br/>AI report"]
        RV2{"Decision"}
        RV1 --> RV2
        RV2 -->|"Approve"| RV3["✅ Approved"]
        RV2 -->|"Edit"| RV4["✏️ Modified & Approved"]
        RV2 -->|"Reject"| RV5["❌ Rejected"]
    end

    style INPUT fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style ORCH fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style TOOLS fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style JUDGE fill:#fce4ec,stroke:#b71c1c,stroke-width:2px
    style REPORT fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style REVIEW fill:#e0f7fa,stroke:#00695c,stroke-width:2px
```

---

## Diagram 2 — System Architecture (Full Stack)

High-level architecture showing frontend, backend, databases, and external services.

```mermaid
flowchart LR
    subgraph CLIENT["Frontend · Next.js 14"]
        FE1["Auth Pages<br/><i>Login / Register</i>"]
        FE2["Agent Chat Interface<br/><i>SSE Pipeline Progress</i>"]
        FE3["Patient Management<br/><i>List / Timeline / Reports</i>"]
        FE4["Report Review<br/><i>Approve / Edit / Reject</i>"]
        FE5["File Upload<br/><i>Images · Audio · Docs</i>"]
    end

    CLIENT <-->|"REST API + SSE<br/>JWT Auth"| BACKEND

    subgraph BACKEND["Backend · FastAPI + Python 3.11"]
        API["API Layer<br/><i>Routes · Auth · CORS</i>"]
        SVC["Services Layer"]
        REPO["Repository Layer<br/><i>SQLAlchemy async</i>"]
        
        API --> SVC
        SVC --> REPO

        subgraph SVC_DETAIL["Services"]
            S1["ClaudeOrchestrator"]
            S2["JudgeService"]
            S3["Tool Registry"]
            S4["SSE Event Bus"]
            S5["Artifact Storage"]
            S6["Whisper ASR<br/><i>Local CPU</i>"]
        end
    end

    BACKEND <-->|"HTTPS"| ANTHROPIC["<b>Anthropic API</b><br/>Claude Sonnet 4<br/><i>Orchestration + Judgment</i>"]

    BACKEND <-->|"HTTPS"| MODAL

    subgraph MODAL["Modal · Serverless GPU"]
        M1["MedGemma 4B<br/><i>A10G · Image Analysis</i>"]
        M2["MedGemma 27B<br/><i>A100-80GB · Text Reasoning</i>"]
        M3["MedSigLIP<br/><i>T4 · Explainability</i>"]
        M4["HeAR<br/><i>T4 · Audio Analysis</i>"]
        M5["MedASR<br/><i>T4 · Dictation</i>"]
    end

    BACKEND <--> DB[("PostgreSQL 16<br/><i>Users · Patients<br/>Timeline · Reports</i>")]

    MODAL -.->|"Model Weights"| HF["🤗 HuggingFace Hub<br/><i>Cached in Modal Volume</i>"]

    style CLIENT fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style BACKEND fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style MODAL fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style DB fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
```

---

## Diagram 3 — Model Zoo & GPU Infrastructure

Detailed view of all AI models, their sizes, hardware, and purposes.

```mermaid
flowchart TD
    subgraph ORCHESTRATOR["🧠 Orchestrator LLM (Cloud API)"]
        CLAUDE["<b>Claude Sonnet 4</b><br/><i>claude-sonnet-4-5-20250929</i><br/>Anthropic API · No GPU<br/><hr/>Roles: Tool routing, Synthesis,<br/>Judge evaluation"]
    end

    subgraph VISION["👁️ Medical Vision"]
        MG4B["<b>MedGemma 4B IT</b><br/><i>google/medgemma-4b-it</i><br/>NVIDIA A10G · 24GB VRAM<br/><hr/>Multimodal image analysis<br/>X-ray · CT · MRI · Derm<br/>Fundus · Histopathology"]

        SIGLIP["<b>MedSigLIP 448</b><br/><i>google/medsiglip-448</i><br/>NVIDIA T4 · 16GB VRAM<br/><hr/>Zero-shot classification<br/>Spatial heatmaps (32×32)<br/>110 conditions · 11 modalities"]
    end

    subgraph TEXT["📝 Clinical Reasoning"]
        MG27B["<b>MedGemma 27B Text IT</b><br/><i>google/medgemma-27b-text-it</i><br/>NVIDIA A100 · 80GB VRAM<br/><hr/>Chain-of-thought reasoning<br/>Evidence citations<br/>Treatment planning<br/>Contraindication detection"]
    end

    subgraph AUDIO["🎧 Medical Audio"]
        HEAR["<b>HeAR</b><br/><i>google/hear-pytorch</i><br/>NVIDIA T4 · 16GB VRAM<br/><hr/>Health Acoustic Representations<br/>Respiratory sound classification<br/>512-dim embeddings"]

        MEDASR["<b>MedASR</b><br/><i>google/medasr</i><br/>NVIDIA T4 · 16GB VRAM<br/><hr/>CTC-based medical ASR<br/>Radiology dictation"]

        WHISPER["<b>OpenAI Whisper</b><br/><i>whisper-base</i><br/>CPU · Local<br/><hr/>Voice input transcription<br/>Frontend dictation"]
    end

    subgraph RAG["📚 Knowledge Retrieval"]
        TFIDF["<b>TF-IDF RAG</b><br/><i>scikit-learn</i><br/>CPU · Local<br/><hr/>Patient history search<br/>Cosine similarity ranking<br/>Prior report enrichment"]
    end

    ORCHESTRATOR -->|"routes to"| VISION
    ORCHESTRATOR -->|"routes to"| TEXT
    ORCHESTRATOR -->|"routes to"| AUDIO
    ORCHESTRATOR -->|"routes to"| RAG

    style ORCHESTRATOR fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style VISION fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style TEXT fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style AUDIO fill:#fce4ec,stroke:#b71c1c,stroke-width:2px
    style RAG fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
```

---

## Diagram 4 — Agentic Loop Detail (Orchestrator Internal)

Shows the internal loop of how Claude decides, dispatches, collects, and optionally re-queries.

```mermaid
sequenceDiagram
    actor Doctor
    participant FE as Frontend<br/>(Next.js)
    participant API as FastAPI<br/>Backend
    participant Claude as Claude Sonnet 4<br/>(Anthropic API)
    participant Tools as Tool Registry<br/>(5 Specialist Tools)
    participant Judge as Judge Agent<br/>(Claude + Structured Output)
    participant DB as PostgreSQL

    Doctor->>FE: Submit case<br/>(images, audio, query, labs)
    FE->>API: POST /analyze/stream
    activate API
    API->>API: SSE: pipeline_start

    Note over API,Claude: Phase 1 — ROUTING
    API->>Claude: System prompt + case data<br/>+ 5 tool schemas
    Claude-->>API: tool_use blocks<br/>[image_analysis, text_reasoning,<br/>history_search, image_explainability]

    Note over API,Tools: Phase 2 — PARALLEL DISPATCH
    API->>API: SSE: tool_start (×N)
    par Parallel Execution
        API->>Tools: image_analysis → MedGemma 4B
        API->>Tools: text_reasoning → MedGemma 27B
        API->>Tools: history_search → Local TF-IDF
        API->>Tools: image_explainability → MedSigLIP
    end
    Tools-->>API: All tool results
    API->>API: SSE: tool_complete (×N)

    Note over API,Claude: Phase 3 — SYNTHESIS
    API->>Claude: Feed tool results back
    Claude-->>API: Brief diagnosis synthesis

    Note over API,Judge: Phase 4 — JUDGE
    API->>API: SSE: phase_start (judging)
    API->>Judge: All tool outputs +<br/>synthesis + patient history
    Judge-->>API: JudgmentResponse<br/>{verdict, confidence,<br/>contradictions, requery_tools}

    alt Verdict = CONFLICT & cycle < 2
        API->>Tools: Re-query only failed tools
        Tools-->>API: Updated results
        API->>Judge: Re-evaluate
        Judge-->>API: Updated verdict
    end

    Note over API,DB: Phase 5 — REPORT
    API->>API: Aggregate findings
    API->>API: Extract heatmap PNGs
    API->>DB: Save FinalReport
    API->>DB: Create TimelineEvent
    API->>API: SSE: done

    API-->>FE: Stream complete
    deactivate API
    FE-->>Doctor: Display interactive report

    Note over Doctor,FE: Human-in-the-Loop
    Doctor->>FE: Approve / Edit / Reject
    FE->>API: POST /cases/approve
    API->>DB: Update report status
```

---

## Diagram 5 — Data Model / Database Schema

```mermaid
erDiagram
    USERS {
        string id PK "UUID"
        string email UK "Unique"
        string hashed_password
        string name
        string role "doctor | admin | nurse"
        boolean is_active
        datetime created_at
    }

    PATIENTS {
        string id PK "PT-XXXXXXXX"
        string name
        date date_of_birth
        string gender
        string medical_record_number
        datetime created_at
    }

    TIMELINE_EVENTS {
        string id PK
        string patient_id FK
        date date
        string event_type "encounter | imaging | lab | procedure | prescription | ai_report"
        string summary
        string source_id
        string source_type
        json metadata
    }

    FINAL_REPORTS {
        string id PK "RPT-XXXXXXXX"
        string encounter_id
        string patient_id FK
        string diagnosis
        float confidence
        string confidence_method
        text evidence_summary
        text timeline_impact
        json plan "treatments, follow-ups"
        json findings "per-tool findings"
        json reasoning_trace "chain-of-thought steps"
        json specialist_outputs "raw tool outputs"
        json judge_verdict "consensus/conflict + details"
        json pipeline_metrics "per-tool timing"
        string approval_status "pending | approved | edited | rejected"
        text doctor_notes
        datetime created_at
    }

    USERS ||--o{ FINAL_REPORTS : "reviews"
    PATIENTS ||--o{ TIMELINE_EVENTS : "has"
    PATIENTS ||--o{ FINAL_REPORTS : "has"
    FINAL_REPORTS ||--o| TIMELINE_EVENTS : "creates"
```

---

## Diagram 6 — Deployment Architecture

```mermaid
flowchart TD
    subgraph DOCKER["Docker Compose · Local / Production"]
        subgraph FE_CONTAINER["Container: frontend"]
            FE["Next.js 14<br/>Port 3000"]
        end
        subgraph BE_CONTAINER["Container: backend"]
            BE["FastAPI<br/>Port 8000<br/>Uvicorn"]
        end
        subgraph DB_CONTAINER["Container: db"]
            PG["PostgreSQL 16<br/>Alpine<br/>Port 5432"]
        end
    end

    FE <-->|"API calls"| BE
    BE <--> PG

    subgraph MODAL_CLOUD["Modal · Serverless GPU Cloud"]
        EP1["medai-medgemma-4b<br/>NVIDIA A10G<br/>24GB VRAM"]
        EP2["medai-medgemma-27b<br/>NVIDIA A100-80GB<br/><i>or L40S (int4)</i>"]
        EP3["medai-siglip-explainability<br/>NVIDIA T4<br/>16GB VRAM"]
        EP4["medai-hear-audio<br/>NVIDIA T4<br/>16GB VRAM"]
        EP5["medai-medasr<br/>NVIDIA T4<br/>16GB VRAM"]
        VOL[("medai-hf-cache<br/>Persistent Volume<br/>Model Weights")]

        EP1 -.-> VOL
        EP2 -.-> VOL
        EP3 -.-> VOL
        EP4 -.-> VOL
        EP5 -.-> VOL
    end

    BE <-->|"HTTPS"| EP1
    BE <-->|"HTTPS"| EP2
    BE <-->|"HTTPS"| EP3
    BE <-->|"HTTPS"| EP4

    subgraph EXTERNAL["External APIs"]
        ANTH["Anthropic API<br/>Claude Sonnet 4"]
        HF["HuggingFace Hub<br/>Model Registry"]
    end

    BE <-->|"HTTPS"| ANTH
    MODAL_CLOUD -.->|"Download weights"| HF

    style DOCKER fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style MODAL_CLOUD fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style EXTERNAL fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

---

## Diagram 7 — SigLIP Explainability Pipeline

Detailed view of how image explainability works with MedSigLIP.

```mermaid
flowchart LR
    IMG["Medical Image<br/><i>e.g. Chest X-ray</i>"] --> PREPROCESS["Resize to 448×448<br/>Normalize"]
    
    MODALITY["Modality Hint<br/><i>xray | ct | mri | ...</i>"] --> TAXONOMY["Condition Taxonomy<br/><i>condition_taxonomy.json</i>"]

    TAXONOMY --> LABELS["Condition Labels<br/><i>e.g. for X-ray:</i><br/>• pneumonia<br/>• pleural effusion<br/>• cardiomegaly<br/>• pneumothorax<br/>• pulmonary nodule<br/>• atelectasis<br/>• TB cavitary lesion<br/>• pulmonary edema<br/>• <i>... 12 total</i>"]

    PREPROCESS --> ENCODER["<b>SigLIP Vision Encoder</b><br/><i>google/medsiglip-448</i><br/>Patch embeddings<br/>14×14 → 32×32 grid"]

    LABELS --> TEXT_ENC["SigLIP Text Encoder<br/>Condition → embeddings"]

    ENCODER --> COSINE["Cosine Similarity<br/>per patch × per condition"]
    TEXT_ENC --> COSINE

    COSINE --> SCORES["Per-Condition<br/>Sigmoid Probabilities<br/><i>Real scores, not LLM-generated</i>"]
    COSINE --> HEATMAPS["Spatial Heatmaps<br/>32×32 activation maps<br/><i>per condition</i>"]

    SCORES --> OUTPUT["Explainability Output"]
    HEATMAPS --> OUTPUT

    OUTPUT --> ARTIFACTS["PNG Heatmap Artifacts<br/>Saved to /storage/RPT-xxx/"]

    style IMG fill:#e3f2fd,stroke:#1565c0
    style ENCODER fill:#f3e5f5,stroke:#6a1b9a
    style OUTPUT fill:#e8f5e9,stroke:#2e7d32
```

---

## Diagram 8 — Authentication & Authorization Flow

```mermaid
sequenceDiagram
    actor Doctor
    participant FE as Frontend
    participant API as FastAPI
    participant DB as PostgreSQL

    Doctor->>FE: Enter email + password
    FE->>API: POST /api/v1/auth/login
    API->>DB: Query user by email
    DB-->>API: User record
    API->>API: Verify bcrypt hash
    API->>API: Generate JWT<br/>(sub=user.id, exp=60min)
    API-->>FE: {token, user}
    FE->>FE: Store token in localStorage

    Note over Doctor,DB: Subsequent requests
    FE->>API: GET /api/v1/patients<br/>Authorization: Bearer <token>
    API->>API: Decode JWT
    API->>DB: Fetch user by ID
    API->>API: Check role<br/>(doctor | admin | nurse)
    API-->>FE: Patient data

    Note over FE,API: Token expired
    FE->>API: Any request with expired token
    API-->>FE: 401 Unauthorized
    FE->>FE: Clear token<br/>Redirect to /auth/login
```

---

## Diagram 9 — Design Patterns Used

```mermaid
mindmap
  root((MedAI<br/>Architecture))
    Agentic Patterns
      Orchestrator-Workers
        Claude routes tasks
        5 specialist tools execute
      Evaluator-Optimizer
        Judge validates consensus
        Re-queries on conflict
        Max 2 cycles
      Human-in-the-Loop
        Doctor approves every output
        Can edit or reject
    Software Patterns
      Repository Pattern
        Interface-based data access
        SQLAlchemy + In-Memory swap
      Registry Pattern
        Tools self-register
        Runtime discovery
      Strategy Pattern
        Mock vs HTTP tools
        Mock vs Real judge
        DEBUG flag toggle
      Dependency Injection
        FastAPI Depends
        lru_cache singletons
    Infrastructure
      Serverless GPU
        Modal auto-scaling
        Pay-per-use inference
      Event-Driven SSE
        Real-time pipeline progress
        contextvars + asyncio Queue
      Domain-Driven Design
        Entities → Interfaces
        Repositories → Services → API
```

---

## Diagram 10 — Patient Timeline & Report Lifecycle

```mermaid
stateDiagram-v2
    [*] --> PatientCreated: Doctor creates patient

    state "Patient Timeline" as Timeline {
        PatientCreated --> HistoricalData: Import medical history
        HistoricalData --> CaseSubmission: Doctor submits new case

        state "AI Analysis" as Analysis {
            CaseSubmission --> Routing: Claude Sonnet 4 routes
            Routing --> ToolExecution: Parallel dispatch
            ToolExecution --> Synthesis: Collect results
            Synthesis --> Judgment: Judge evaluates
            Judgment --> ReportGenerated: Consensus ✅
            Judgment --> ToolExecution: Conflict ❌ (retry)
        }

        ReportGenerated --> PendingReview: Report saved
        
        state "Doctor Review" as Review {
            PendingReview --> Approved: Doctor approves ✅
            PendingReview --> Edited: Doctor edits ✏️
            PendingReview --> Rejected: Doctor rejects ❌
        }

        Approved --> TimelineUpdated: Add to patient record
        Edited --> TimelineUpdated: Add modified to record
        Rejected --> TimelineUpdated: Mark as rejected

        TimelineUpdated --> CaseSubmission: Next case uses\nhistory context via RAG
    }

    TimelineUpdated --> [*]

    note right of Analysis
        Each analysis creates:
        - FinalReport in DB
        - TimelineEvent (AI_REPORT)
        - Heatmap PNGs in /storage/
    end note
```

---

## Diagram 11 — Technology Stack Overview

```mermaid
flowchart TB
    subgraph FRONTEND["🖥️ Frontend Layer"]
        direction LR
        NEXT["Next.js 14"]
        TS["TypeScript"]
        TAIL["Tailwind CSS"]
        ZUSTAND["Zustand<br/><i>State Management</i>"]
        TANSTACK["TanStack Query<br/><i>Data Fetching</i>"]
    end

    subgraph BACKEND_LAYER["⚙️ Backend Layer"]
        direction LR
        FASTAPI["FastAPI"]
        PYDANTIC["Pydantic v2"]
        SQLA["SQLAlchemy<br/><i>Async</i>"]
        ALEMBIC["Alembic<br/><i>Migrations</i>"]
        JOSE["python-jose<br/><i>JWT</i>"]
    end

    subgraph AI_LAYER["🤖 AI / ML Layer"]
        direction LR
        ANTHROPIC_SDK["Anthropic SDK<br/><i>Claude API</i>"]
        TORCH["PyTorch"]
        HF_TF["HuggingFace<br/>Transformers"]
        SKLEARN["scikit-learn<br/><i>TF-IDF</i>"]
        WHISPER_LIB["OpenAI Whisper"]
    end

    subgraph INFRA_LAYER["☁️ Infrastructure"]
        direction LR
        DOCKER_COMP["Docker Compose"]
        MODAL_SDK["Modal<br/><i>Serverless GPU</i>"]
        POSTGRES["PostgreSQL 16"]
        GCP_ALT["GCP Cloud Run<br/><i>Alternative</i>"]
    end

    FRONTEND --> BACKEND_LAYER
    BACKEND_LAYER --> AI_LAYER
    BACKEND_LAYER --> INFRA_LAYER

    style FRONTEND fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style BACKEND_LAYER fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style AI_LAYER fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style INFRA_LAYER fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
```
