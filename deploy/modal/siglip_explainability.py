"""Modal deployment — MedSigLIP Explainability Service.

Serves zero-shot medical image explainability via per-patch text similarity.
Produces spatial heatmaps (pure activation maps, no overlay) and condition
probabilities using torch.sigmoid (real contrastive scores, not LLM-generated).

Model: google/medsiglip-448 — medically fine-tuned SigLIP (CXR, derm,
ophthalmology, histopathology, CT, MRI). Same encoder powering MedGemma vision.

GPU: T4 (16 GB) — MedSigLIP 400M+400M at fp16 uses ~1.8 GB VRAM.
Image: 448×448, patch_size=14 → 32×32 = 1024 patches.

Deploy:  modal deploy deploy/modal/siglip_explainability.py
Test:    modal run deploy/modal/siglip_explainability.py
Logs:    modal app logs medai-siglip-explainability
"""

from __future__ import annotations

import modal

# ── Modal resources ────────────────────────────────────────

app = modal.App("medai-siglip-explainability")

# Persistent volume to cache model weights (shared with MedGemma endpoints)
hf_cache = modal.Volume.from_name("medai-hf-cache", create_if_missing=True)

# Container image with all deps pre-installed
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.5.0",
        "transformers>=4.50.0",
        "accelerate>=1.2.0",
        "pillow>=10.0.0",
        "pydantic>=2.10.0",
        "fastapi>=0.115.0",
        "sentencepiece>=0.2.0",
        "matplotlib>=3.9.0",
        "numpy>=1.26.0",
    )
)


# ── Model class ────────────────────────────────────────────

@app.cls(
    image=image,
    gpu="T4",  # 16 GB — MedSigLIP 0.8B at fp16 uses ~1.8 GB
    timeout=300,
    scaledown_window=900,  # Keep warm for 15 min after last request
    secrets=[modal.Secret.from_name("huggingface-secret")],
    volumes={"/root/.cache/huggingface": hf_cache},
)
class SigLIPExplainability:
    """MedSigLIP — zero-shot medical image explainability.

    google/medsiglip-448: medically fine-tuned SigLIP trained on CXR, derm,
    ophthalmology, histopathology, CT, MRI image-text pairs. Same vision
    encoder that powers MedGemma.

    Produces:
    - Per-condition sigmoid probabilities (real contrastive scores)
    - Per-condition spatial heatmaps (32×32 upscaled, pure activation maps)
    - Optional image embeddings for future similarity search
    """

    model_id: str = "google/medsiglip-448"
    image_size: int = 448  # MedSigLIP native resolution
    grid_size: int = 32  # 448 // 14 = 32 patches per side

    @modal.enter()
    def load_model(self):
        """Load model on container startup (cached in volume)."""
        import torch
        from transformers import AutoModel, AutoProcessor

        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = AutoModel.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            device_map="auto",
            attn_implementation="sdpa",  # memory-efficient, no attention weights needed
        )
        self.model.eval()

        # Commit downloaded weights to volume for caching
        hf_cache.commit()

        print(f"✅ {self.model_id} loaded on {torch.cuda.get_device_name()}")

    def _generate_heatmap_png(self, similarity_1d, colormap_name: str = "inferno") -> bytes:
        """Convert a 1024-length similarity vector to a 448×448 colormapped PNG.

        Returns raw PNG bytes — pure activation map, no original image overlay.
        """
        import io

        import matplotlib
        import matplotlib.cm as cm
        import numpy as np
        from PIL import Image as PILImage

        matplotlib.use("Agg")  # non-interactive backend

        # Reshape to spatial grid
        heatmap = similarity_1d.reshape(self.grid_size, self.grid_size)

        # Normalize to [0, 1]
        h_min, h_max = heatmap.min(), heatmap.max()
        if h_max - h_min > 1e-8:
            heatmap = (heatmap - h_min) / (h_max - h_min)
        else:
            heatmap = np.zeros_like(heatmap)

        # Apply colormap
        colormap = cm.get_cmap(colormap_name)
        colored = colormap(heatmap)  # (32, 32, 4) RGBA float [0,1]
        colored_uint8 = (colored[:, :, :3] * 255).astype(np.uint8)  # drop alpha, RGB

        # Upscale to 448×448 with bicubic interpolation
        pil_heatmap = PILImage.fromarray(colored_uint8).resize(
            (self.image_size, self.image_size), PILImage.BICUBIC
        )

        # Encode to PNG bytes
        buf = io.BytesIO()
        pil_heatmap.save(buf, format="PNG")
        return buf.getvalue()

    @modal.fastapi_endpoint(method="POST", docs=True)
    def explain(self, request: dict) -> dict:
        """Zero-shot explainability: score image against condition labels.

        Request body:
            image_url: str               — URL of the medical image (optional if image_base64 is provided)
            image_base64: str            — Base64-encoded image bytes (optional if image_url is provided)
            condition_labels: list[str]  — Text descriptions of conditions to check
            modality_hint: str           — Optional: prepend to each label for context
            return_embedding: bool       — Return image embedding vector (default: false)
            top_k_heatmaps: int          — Max heatmaps to return (default: 5, -1 = all)

        Returns:
            scores:          list of {label, probability} sorted desc
            heatmaps:        list of {label, heatmap_base64} — pure activation maps
            image_embedding: list[float] | null
            inference_time_ms: float
            model_id:        str
        """
        import base64
        import io
        import time
        import traceback

        import httpx
        import numpy as np
        import torch
        import torch.nn.functional as F
        from PIL import Image

        try:
            image_url = request.get("image_url", "")
            image_b64 = request.get("image_base64", "")
            labels = request.get("condition_labels", [])
            modality_hint = request.get("modality_hint", "")
            return_embedding = request.get("return_embedding", False)
            top_k = request.get("top_k_heatmaps", 5)

            if not image_url and not image_b64:
                return {"error": "image_url or image_base64 is required"}
            if not labels:
                return {"error": "condition_labels is required (non-empty list)"}

            # ── Load image (base64 preferred, URL as fallback) ──
            if image_b64:
                # Strip data URI prefix if present
                if "," in image_b64:
                    image_b64 = image_b64.split(",", 1)[1]
                img_bytes = base64.b64decode(image_b64)
                pil_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            else:
                with httpx.Client(
                    timeout=30.0,
                    follow_redirects=True,
                    headers={"User-Agent": "MedAI-SigLIP/1.0"},
                ) as client:
                    img_response = client.get(image_url)
                    img_response.raise_for_status()
                pil_image = Image.open(io.BytesIO(img_response.content)).convert("RGB")

            # ── Prepare text labels with modality context ──
            if modality_hint:
                texts = [f"{modality_hint} showing {label}" for label in labels]
            else:
                texts = list(labels)

            # ── Process inputs ─────────────────────────────
            inputs = self.processor(
                text=texts,
                images=pil_image,
                padding="max_length",  # CRITICAL: SigLIP trained with max_length padding
                return_tensors="pt",
            ).to(self.model.device)

            # ── Inference ──────────────────────────────────
            t0 = time.monotonic()

            with torch.no_grad():
                # Full model forward for global scores
                outputs = self.model(**inputs)
                global_probs = torch.sigmoid(outputs.logits_per_image)[0]  # (N_labels,)

                # Per-patch hidden states for spatial heatmaps
                vision_outputs = self.model.vision_model(
                    pixel_values=inputs["pixel_values"],
                )
                patch_embeds = vision_outputs.last_hidden_state  # (1, 1024, D)
                patch_embeds = F.normalize(patch_embeds, dim=-1)

                # Text embeddings (already projected)
                text_embeds = outputs.text_embeds  # (N_labels, D)
                text_embeds = F.normalize(text_embeds, dim=-1)

                # Per-patch similarity: (N_labels, 1024)
                patch_similarities = torch.einsum(
                    "ld,bpd->lp", text_embeds, patch_embeds
                )[..., :]  # shape: (N_labels, 1024)

            inference_time_ms = round((time.monotonic() - t0) * 1000, 1)

            # ── Build scores ───────────────────────────────
            # MedSigLIP uses sigmoid contrastive loss — logits can be very
            # negative, producing near-zero sigmoid values.  We expose both
            # the sigmoid probability AND a softmax-normalised probability
            # (as per the official model card example) so the backend / UI
            # can pick the more informative one.
            raw_logits = outputs.logits_per_image[0].cpu().float()  # (N_labels,)
            sigmoid_probs = global_probs.cpu().float()               # already sigmoided
            softmax_probs = torch.softmax(raw_logits, dim=0)

            scores = sorted(
                [
                    {
                        "label": label,
                        "probability": round(float(softmax_probs[i]), 6),
                        "sigmoid_score": round(float(sigmoid_probs[i]), 8),
                        "raw_logit": round(float(raw_logits[i]), 4),
                    }
                    for i, label in enumerate(labels)
                ],
                key=lambda x: -x["probability"],
            )

            # ── Build heatmaps (pure activation maps) ──────
            heatmaps = []
            # Determine which labels get heatmaps
            if top_k < 0:
                heatmap_labels = [s["label"] for s in scores]
            else:
                heatmap_labels = [s["label"] for s in scores[:top_k]]

            label_to_idx = {label: i for i, label in enumerate(labels)}

            for label in heatmap_labels:
                idx = label_to_idx[label]
                sim = patch_similarities[idx].cpu().float().numpy()
                png_bytes = self._generate_heatmap_png(sim)
                b64 = base64.b64encode(png_bytes).decode("ascii")
                heatmaps.append({
                    "label": label,
                    "heatmap_base64": b64,
                })

            # ── Build response ─────────────────────────────
            result: dict = {
                "scores": scores,
                "heatmaps": heatmaps,
                "inference_time_ms": inference_time_ms,
                "model_id": self.model_id,
            }

            if return_embedding:
                img_emb = outputs.image_embeds[0].cpu().float().tolist()
                result["image_embedding"] = img_emb
            else:
                result["image_embedding"] = None

            return result

        except Exception as e:
            return {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "scores": [],
                "heatmaps": [],
            }


# ── Local test entrypoint ──────────────────────────────────

@app.local_entrypoint()
def main():
    """Quick smoke test — call the deployed web endpoint via HTTP.

    Since explain() is a @modal.fastapi_endpoint, it cannot be invoked
    via .remote() or .local() with GPU deps.  We call the deployed URL
    directly with httpx instead.
    """
    import base64
    import json
    import os
    import sys

    import httpx   # available in local .venv

    # Resolve deployed endpoint URL (same as backend/.env)
    default_url = (
        "https://arseniistratiuk--medai-siglip-explainability"
        "-siglipexpla-d89533.modal.run"
    )
    endpoint = os.environ.get("MEDSIGLIP_ENDPOINT", default_url)

    # Use a public Google Storage image that won't 403
    # (SCIN dermatology dataset — used in MedSigLIP training/eval)
    test_url = "https://storage.googleapis.com/dx-scin-public-data/dataset/images/3445096909671059178.png"

    payload = {
        "image_url": test_url,
        "condition_labels": [
            "a photo of skin with a rash or lesion",
            "a photo of normal healthy skin",
            "consolidation consistent with pneumonia",
            "cardiomegaly with enlarged heart silhouette",
            "normal healthy lung fields",
        ],
        "modality_hint": "dermatology",
        "return_embedding": True,
        "top_k_heatmaps": 3,
    }

    print(f"🔬 Calling deployed MedSigLIP endpoint:")
    print(f"   {endpoint}")
    print(f"   Labels: {len(payload['condition_labels'])}")
    print()

    with httpx.Client(timeout=180.0) as client:
        resp = client.post(endpoint, json=payload)
        if resp.status_code != 200:
            print(f"❌ HTTP {resp.status_code}: {resp.text[:500]}")
            sys.exit(1)
        result = resp.json()

    if "error" in result and result["error"]:
        print(f"❌ Endpoint error: {result['error']}")
        if "traceback" in result:
            print(result["traceback"][:1000])
        sys.exit(1)

    # Print scores (exclude heatmap base64 for readability)
    display = {k: v for k, v in result.items() if k != "heatmaps"}
    if "image_embedding" in display and display["image_embedding"]:
        display["image_embedding"] = f"[{len(display['image_embedding'])} dims]"
    print(json.dumps(display, indent=2))

    # Validate heatmaps
    for hm in result.get("heatmaps", []):
        png_data = base64.b64decode(hm["heatmap_base64"])
        assert png_data[:4] == b"\x89PNG", f"Invalid PNG for {hm['label']}"
        print(f"  ✅ Heatmap for '{hm['label']}': {len(png_data)} bytes (valid PNG)")

    print(f"\n{'='*50}")
    print(f"  Model:     {result.get('model_id', '?')}")
    print(f"  Scores:    {len(result.get('scores', []))} conditions")
    print(f"  Heatmaps:  {len(result.get('heatmaps', []))} generated")
    print(f"  Inference: {result.get('inference_time_ms', '?')} ms")
    print(f"{'='*50}")
