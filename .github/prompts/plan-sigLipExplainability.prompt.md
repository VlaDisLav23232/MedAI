# SigLIP Explainability Integration (Modal + Backend)

Deploy SigLIP (google/siglip-so400m-patch14-384) on Modal as a zero-shot explainability service producing per-patch text-conditioned heatmaps. Add a new `IMAGE_EXPLAINABILITY` tool to the existing tool system by extending (not modifying) the `ToolName` enum, `ToolOutput` union, tool classes, and registry. Heatmaps flow into the existing `heatmap_urls` response field with zero changes to `backend/src/medai/api/routes/cases.py`. Per-modality condition label taxonomy is configurable as a JSON file with request-level overrides.

The architecture choice — **per-patch cosine similarity** with text embeddings — is the best fit for SigLIP: no CLS token exists in SigLIP (it uses attention-based pooling), so attention rollout/GradCAM are either poorly defined or require gradient computation. Per-patch similarity is gradient-free, fast, and gives text-conditioned spatial maps (different conditions highlight different ROIs). This is the unique explainability SigLIP provides that MedGemma cannot.

---

## Why SigLIP Probabilities Are Real

SigLIP probabilities are fundamentally different from LLM self-reported confidence:

| Aspect | LLM Self-Reported | SigLIP Sigmoid |
|---|---|---|
| **How computed** | Model *generates text* like "0.85" — predicting what a doctor would write | **Geometric** — dot product of learned embeddings → `torch.sigmoid()` |
| **Training objective** | Next-token prediction (not optimized for calibration) | Binary sigmoid contrastive loss — *directly trained* to produce match/no-match probabilities |
| **Independence** | N/A | Each (image, text) score is independent — multiple conditions can score high simultaneously (critical for medical multi-label) |
| **Reproducible** | No — different temperature/prompt → different number | **Yes** — deterministic forward pass, same input → same score |

**Caveat**: SigLIP scores are *similarity probabilities* ("how well does this image match this text description?"), not *diagnostic probabilities* ("what is the chance this patient has pneumonia?"). Trained on WebLI (web-scale data), not clinically calibrated medical datasets.

Transparency for UI: `confidence_method: "siglip_patch_similarity"` with tooltip: *"Vision-language similarity score (0–1). Higher = stronger visual match to this condition. Not a calibrated diagnostic probability."*

---

## Heatmap Design

**Heatmaps are completely separate from the input image.** The Modal endpoint returns pure activation maps (single-channel grayscale/colormapped PNGs). The frontend controls overlay: transparency slider, toggle per-condition, side-by-side.

Modal response shape:
```json
{
  "scores": [{"label": "...", "probability": 0.82}],
  "heatmaps": [
    {"label": "pneumonia consolidation", "heatmap_base64": "<raw grayscale/colormap PNG>"},
    {"label": "pleural effusion", "heatmap_base64": "<separate PNG>"}
  ],
  "image_embedding": [0.012, -0.034, ...],
  "inference_time_ms": 142.3,
  "model_id": "google/siglip-so400m-patch14-384"
}
```

Local test script saves each result separately:
- `output/heatmap_{condition}.png` — raw activation map
- `output/overlay_{condition}.png` — composited over original at alpha=0.4

---

## Self-Critique

- *SigLIP wasn't trained on medical images* — true, but zero-shot transfer works with descriptive clinical text labels (validated in literature); raw sigmoid probabilities are exposed transparently, never claimed as calibrated accuracy
- *Base64 heatmaps in JSON responses* — adds ~50-100KB per heatmap; acceptable for prototype, `str` field type allows real URLs later when GCP team adds cloud storage
- *Merge conflicts risk* — all changes are purely additive (new enum values, new classes, new files); no existing class/method is modified

---

## Steps

### 1. Modal Deployment Script

Create `deploy/modal/siglip_explainability.py`:
- `modal.App("medai-siglip-explainability")` with `gpu="T4"` (16 GB — model is ~1.8 GB at fp16, massive headroom)
- Reuse existing `modal.Volume.from_name("medai-hf-cache")` pattern from `deploy/modal/medgemma_4b.py`
- `@modal.enter()` loads `google/siglip-so400m-patch14-384` via `AutoModel.from_pretrained(torch_dtype=torch.float16, attn_implementation="sdpa")`
- Single `@modal.fastapi_endpoint(method="POST")` accepting `{image_url, condition_labels: list[str], modality_hint, return_embedding: bool, top_k_heatmaps: int}`
- **Heatmap generation**: per-patch text similarity — get `vision_model(...).last_hidden_state` (shape `(1, 729, D)`), compute `F.normalize` then `torch.einsum("bd,bpd->bp", text_embed, patch_embeds)`, reshape to 27×27, upsample to 384×384, apply matplotlib `inferno` colormap, encode as base64 data URI
- **Heatmaps are pure activation maps** — no original image composited; single-channel colormap only
- Returns: `{scores: [{label, probability}], heatmaps: [{label, heatmap_base64}], image_embedding: list[float]|null, inference_time_ms, model_id}`
- `scaledown_window=900` (matches existing pattern)
- `@app.local_entrypoint()` with a real public chest X-ray for smoke testing

**Test**: `modal run deploy/modal/siglip_explainability.py` — verify JSON response, probabilities in [0,1], heatmap is valid base64 PNG.

### 2. Condition Label Taxonomy

Create `backend/src/medai/tools/condition_taxonomy.json`:
- JSON mapping `Modality` enum values → list of descriptive condition labels
- Example for `xray`: `["consolidation consistent with pneumonia", "pleural effusion", "cardiomegaly with enlarged heart silhouette", "pneumothorax", "pulmonary nodule", "normal lung fields", "atelectasis", "tuberculosis with cavitary lesion"]`
- Cover all 11 `Modality` values from `backend/src/medai/domain/entities.py` (`xray`, `ct`, `mri`, `ultrasound`, `fundus`, `dermatology`, `histopathology`, `pet`, `mammography`, `endoscopy`, `other`)
- Add `siglip_taxonomy_path` setting to `backend/src/medai/config.py` pointing to this file

**Test**: Python script — load JSON, assert all 11 modalities present, no empty label lists.

### 3. Domain Entities

Extend `backend/src/medai/domain/entities.py` (purely additive):
- Add `IMAGE_EXPLAINABILITY = "image_explainability"` to `ToolName` enum
- Add `SIGLIP_PATCH_SIMILARITY = "siglip_patch_similarity"` to `ConfidenceMethod` enum
- Create `ConditionScore(BaseModel)`: `label: str`, `probability: float` (0-1, sigmoid), `heatmap_data_uri: str | None`
- Create `ImageExplainabilityOutput(BaseModel)`: `tool`, `modality_detected`, `condition_scores: list[ConditionScore]`, `attention_heatmap_url: str | None` (top-finding heatmap — triggers auto-extraction in `cases.py`), `embedding: list[float] | None`, `inference: InferenceMetadata | None`
- Extend `ToolOutput` union: add `| ImageExplainabilityOutput`

Key: `attention_heatmap_url` field name matches existing extraction logic in `cases.py` lines 49-50 → heatmaps flow into `CaseAnalysisResponse.heatmap_urls` with **zero route changes**.

**Test**: Unit test — entity serialization/deserialization, field constraints, JSON round-trip.

### 4. HTTP Tool Implementation

Add `HttpSigLipTool` class to `backend/src/medai/tools/http.py`:
- Extends `_HttpToolBase` (inherits retry, timeout, error handling)
- `name` → `ToolName.IMAGE_EXPLAINABILITY`
- `description` → "Generate visual explainability heatmaps for medical images using zero-shot classification. Highlights which image regions match clinical conditions. Returns per-condition similarity probabilities and spatial activation maps."
- `input_schema` → `{image_url: str (required), modality_hint: str (enum), clinical_context: str, condition_labels: list[str] (optional override)}`
- `_build_request_payload()` — loads taxonomy from JSON for given `modality_hint`, merges with any request-provided `condition_labels`
- `_parse_response()` → builds `ImageExplainabilityOutput`
- Add to `register_http_tools()` factory: `ToolName.IMAGE_EXPLAINABILITY: HttpSigLipTool(endpoint=settings.medsiglip_endpoint)`

**Test**: Unit tests (respx-mocked) — payload construction with taxonomy, response parsing, label merger, retry.

### 5. Mock Tool

Add `MockImageExplainabilityTool` class to `backend/src/medai/tools/mock.py`:
- Returns realistic `ImageExplainabilityOutput` with sample condition scores (realistic probability distribution)
- Mock `attention_heatmap_url` as placeholder path
- Add to `register_mock_tools()` factory

**Test**: Run full existing test suite (`pytest backend/tests/unit/`) — all 122+ tests pass, new mock tool in registry.

### 6. Dependency Injection + Orchestrator Wiring

Minimal edits:
- Tool already included by `register_mock_tools()` / `register_http_tools()` factories from Steps 4-5
- `ORCHESTRATOR_SYSTEM_PROMPT` in `backend/src/medai/services/orchestrator.py` — add rule: `"5b. Use image_explainability alongside image_analysis when medical images are provided — it generates spatial heatmaps showing which regions triggered each finding."`
- `MockOrchestrator.analyze_case()` — add `IMAGE_EXPLAINABILITY` to `tools_to_call` when `request.image_urls` present

**Test**: Full test suite. Mock E2E (`DEBUG=true`): `POST /api/v1/cases/analyze` with image_urls → verify `heatmap_urls` populated, `image_explainability` in `specialist_summaries` and `pipeline_metrics.tools_called`.

### 7. Local Test Script

Create `scripts/test_siglip_local.py`:
1. Call Modal endpoint with a real X-ray
2. Save each raw heatmap as separate PNG: `output/heatmap_{condition}.png`
3. Save overlay composites separately: load original, apply heatmap at alpha=0.4, save as `output/overlay_{condition}.png`
4. Print probability table to stdout
5. Assert: all probabilities ∈ [0,1], at least one heatmap non-uniform, dimensions match

### 8. Deploy & Live E2E

- `modal deploy deploy/modal/siglip_explainability.py` — get endpoint URL
- Set `MEDSIGLIP_ENDPOINT=<modal_url>` in `.env`
- Update `deploy/modal/deploy_all.sh` to include siglip script
- Run live E2E with `DEBUG=false` — real X-ray through full pipeline (Claude → IMAGE_ANALYSIS + IMAGE_EXPLAINABILITY parallel → JUDGE → REPORT)
- Verify: real SigLIP probabilities (no stubs), real heatmaps (visually inspect), timing in `pipeline_metrics`

---

## Verification Matrix

| Step | What to test | How |
|---|---|---|
| 1 | Modal endpoint works | `modal run deploy/modal/siglip_explainability.py` |
| 2 | Taxonomy coverage | Python script: load JSON, assert all 11 modalities |
| 3 | Domain entities | `pytest -k "test_explainability"` — serialization round-trip |
| 4 | HTTP tool unit | `pytest backend/tests/unit/test_siglip_tool.py` — respx mocked |
| 5 | Existing tests | `pytest backend/tests/unit/` — all 122+ pass, no regressions |
| 6 | Mock E2E | `DEBUG=true`, `curl POST /api/v1/cases/analyze` with images |
| 7 | Local test script | `python scripts/test_siglip_local.py` — visual + numeric check |
| 8 | Live E2E | `DEBUG=false`, real Modal endpoint, real X-ray image |

---

## Files Created (zero conflict)

- `deploy/modal/siglip_explainability.py`
- `backend/src/medai/tools/condition_taxonomy.json`
- `backend/tests/unit/test_siglip_tool.py`
- `scripts/test_siglip_local.py`

## Files Modified (minimal, additive only)

- `backend/src/medai/domain/entities.py` — add enum value + 2 new entities + extend union
- `backend/src/medai/tools/http.py` — add `HttpSigLipTool` class + 1 line in factory
- `backend/src/medai/tools/mock.py` — add `MockImageExplainabilityTool` class + 1 line in factory
- `backend/src/medai/services/orchestrator.py` — add 1 rule to system prompt + 4 lines in MockOrchestrator
- `backend/src/medai/config.py` — add `siglip_taxonomy_path` field
- `deploy/modal/deploy_all.sh` — add 1 deploy line

---

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Heatmap method | Per-patch text similarity | SigLIP has no CLS token; gradient-free; text-conditioned spatial maps |
| Tool type | Separate `IMAGE_EXPLAINABILITY` | Different model, different function (explainability vs diagnosis); Claude dispatches both in parallel |
| GPU | T4 (16 GB) | 1.8 GB model at fp16; cheapest Modal option; massive headroom |
| Heatmap format | Separate base64 PNGs (no overlay) | Frontend controls transparency/overlay; local tests save separately + composite |
| Heatmap encoding | Pure activation map, no original image | Clean separation; UI manages overlay |
| Taxonomy | JSON config defaults + request overrides | No hardcoding; extensible without code changes |
| `attention_heatmap_url` | Top-scoring condition's heatmap | Triggers existing auto-extraction in cases.py; zero route changes |

## Prerequisites

- Modal account + CLI: `pip install modal && modal token new`
- HuggingFace token as Modal secret: `modal secret create huggingface-secret HUGGING_FACE_HUB_TOKEN=hf_...`
- `google/siglip-so400m-patch14-384` — Apache 2.0 license, no gated access
