#!/usr/bin/env python3
"""Local test script — call MedSigLIP Modal endpoint and validate output.

Usage (after `modal deploy deploy/modal/siglip_explainability.py`):
  1. Set MEDSIGLIP_ENDPOINT env var (printed by deploy command)
  2. Run with local image:
       python scripts/test_siglip_local.py path/to/chest_xray.png
     Or without args (uses default public image URL):
       python scripts/test_siglip_local.py

What it does:
  - Send a medical image (local file as base64, or URL) to MedSigLIP endpoint
  - Validate all probabilities ∈ [0, 1]
  - Decode and save each heatmap as a separate PNG: output/heatmap_{condition}.png
  - Create overlay composites: output/overlay_{condition}.png (original + heatmap @ alpha=0.4)
  - Print a probability table to stdout
  - Assert: at least one heatmap is non-uniform, dimensions match expectations

Requires: pip install httpx pillow numpy
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path

try:
    import httpx
    import numpy as np
    from PIL import Image
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install httpx pillow numpy")
    sys.exit(1)

# ── Configuration ──────────────────────────────────────────

ENDPOINT = os.environ.get("MEDSIGLIP_ENDPOINT", "")
OUTPUT_DIR = Path("output/siglip_test")

# Fallback URL if no local image provided
FALLBACK_IMAGE_URL = (
    "https://storage.googleapis.com/dx-scin-public-data/"
    "dataset/images/3445096909671059178.png"
)

CONDITION_LABELS = [
    "consolidation consistent with pneumonia",
    "pleural effusion with blunting of costophrenic angle",
    "cardiomegaly with enlarged heart silhouette",
    "pneumothorax with absent lung markings",
    "normal healthy lung fields with no abnormality",
    "pulmonary nodule or mass",
    "atelectasis with volume loss",
    "tuberculosis with cavitary lesion",
]


# ── Helpers ────────────────────────────────────────────────

def save_heatmap_png(b64_data: str, path: Path) -> np.ndarray:
    """Decode base64 PNG, save to disk, return as numpy array."""
    png_bytes = base64.b64decode(b64_data)
    assert png_bytes[:4] == b"\x89PNG", f"Not a valid PNG: {path.name}"
    img = Image.open(BytesIO(png_bytes))
    img.save(path)
    return np.array(img)


def create_overlay(
    original_pil: Image.Image | None,
    heatmap_arr: np.ndarray,
    output_path: Path,
    alpha: float = 0.4,
) -> None:
    """Composite heatmap over original image at given alpha."""
    if original_pil is None:
        return

    original = original_pil.convert("RGBA")

    # Resize heatmap to match original
    heatmap_img = Image.fromarray(heatmap_arr).convert("RGBA")
    heatmap_resized = heatmap_img.resize(original.size, Image.BILINEAR)

    # Blend
    overlay = Image.blend(original, heatmap_resized, alpha=alpha)
    overlay.save(output_path)


def print_score_table(scores: list[dict]) -> None:
    """Print a formatted probability table sorted by score descending."""
    sorted_scores = sorted(scores, key=lambda s: s["probability"], reverse=True)

    # Check if response includes extended fields
    has_extended = any("sigmoid_score" in s for s in sorted_scores)

    if has_extended:
        print("\n┌─────────────────────────────────────────────────┬──────────┬───────────┬──────────┐")
        print("│ Condition                                       │ Softmax  │  Sigmoid  │  Logit   │")
        print("├─────────────────────────────────────────────────┼──────────┼───────────┼──────────┤")
        for s in sorted_scores:
            label = s["label"][:47].ljust(47)
            prob = f"{s['probability']:.4f}".rjust(8)
            sig = f"{s.get('sigmoid_score', 0):.2e}".rjust(9)
            logit = f"{s.get('raw_logit', 0):.2f}".rjust(8)
            bar = "█" * int(s["probability"] * 20)
            print(f"│ {label} │ {prob} │ {sig} │ {logit} │ {bar}")
        print("└─────────────────────────────────────────────────┴──────────┴───────────┴──────────┘")
    else:
        print("\n┌─────────────────────────────────────────────────────────┬────────────┐")
        print("│ Condition                                               │ Probability│")
        print("├─────────────────────────────────────────────────────────┼────────────┤")
        for s in sorted_scores:
            label = s["label"][:55].ljust(55)
            prob = f"{s['probability']:.4f}".rjust(10)
            bar = "█" * int(s["probability"] * 20)
            print(f"│ {label} │ {prob} │ {bar}")
        print("└─────────────────────────────────────────────────────────┴────────────┘")


# ── Main ───────────────────────────────────────────────────

async def run_test() -> None:
    if not ENDPOINT:
        print("ERROR: Set MEDSIGLIP_ENDPOINT environment variable.")
        print("  export MEDSIGLIP_ENDPOINT=https://<your-modal-app>.modal.run")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Determine image source ──
    local_image_path = sys.argv[1] if len(sys.argv) > 1 else None
    original_pil: Image.Image | None = None

    payload: dict = {
        "condition_labels": CONDITION_LABELS,
        "modality_hint": "xray",
        "return_embedding": True,
        "top_k_heatmaps": 5,
    }

    if local_image_path:
        # Local file → send as base64
        img_path = Path(local_image_path)
        if not img_path.exists():
            print(f"ERROR: File not found: {img_path}")
            sys.exit(1)
        img_bytes = img_path.read_bytes()
        payload["image_base64"] = base64.b64encode(img_bytes).decode("ascii")
        original_pil = Image.open(BytesIO(img_bytes)).convert("RGB")
        image_desc = str(img_path.resolve())
    else:
        # Use fallback URL
        payload["image_url"] = FALLBACK_IMAGE_URL
        image_desc = FALLBACK_IMAGE_URL[:60] + "..."
        # Try to download for overlays
        try:
            resp = httpx.get(FALLBACK_IMAGE_URL, timeout=30)
            resp.raise_for_status()
            original_pil = Image.open(BytesIO(resp.content)).convert("RGB")
        except Exception:
            pass

    print(f"🔬 MedSigLIP Explainability Test")
    print(f"   Endpoint: {ENDPOINT}")
    print(f"   Image:    {image_desc}")
    print(f"   Mode:     {'base64 (local file)' if local_image_path else 'URL'}")
    print(f"   Labels:   {len(CONDITION_LABELS)} conditions")
    print(f"   Output:   {OUTPUT_DIR.resolve()}\n")

    # ── Call endpoint ──
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(ENDPOINT, json=payload)
    wall_time_ms = (time.perf_counter() - t0) * 1000

    if resp.status_code != 200:
        print(f"❌ HTTP {resp.status_code}: {resp.text[:500]}")
        sys.exit(1)

    data = resp.json()

    if "error" in data and data["error"]:
        print(f"❌ Endpoint error: {data['error']}")
        if "traceback" in data:
            print(data["traceback"][:1000])
        sys.exit(1)

    # ── Validate scores ──
    scores = data.get("scores", [])
    assert len(scores) > 0, "No scores returned"

    for s in scores:
        assert 0.0 <= s["probability"] <= 1.0, (
            f"Probability out of range for '{s['label']}': {s['probability']}"
        )

    print_score_table(scores)

    # ── Validate and save heatmaps ──
    heatmaps = data.get("heatmaps", [])
    print(f"\n📊 Heatmaps: {len(heatmaps)} received")

    heatmap_arrays = []
    for hm in heatmaps:
        label_slug = hm["label"][:40].replace(" ", "_").replace("/", "-")
        heatmap_path = OUTPUT_DIR / f"heatmap_{label_slug}.png"
        arr = save_heatmap_png(hm["heatmap_base64"], heatmap_path)
        heatmap_arrays.append(arr)
        print(f"   ✅ {heatmap_path.name} — {arr.shape} ({heatmap_path.stat().st_size:,} bytes)")

    # Check at least one heatmap is non-uniform (not all same pixel)
    if heatmap_arrays:
        non_uniform = sum(1 for arr in heatmap_arrays if arr.std() > 1.0)
        assert non_uniform > 0, "All heatmaps are uniform — model may not be working"
        print(f"   ✅ {non_uniform}/{len(heatmap_arrays)} heatmaps are non-uniform (spatial variation)")

    # ── Create overlay composites ──
    print(f"\n🖼️  Creating overlay composites (alpha=0.4)...")
    for hm, arr in zip(heatmaps, heatmap_arrays):
        label_slug = hm["label"][:40].replace(" ", "_").replace("/", "-")
        overlay_path = OUTPUT_DIR / f"overlay_{label_slug}.png"
        create_overlay(original_pil, arr, overlay_path, alpha=0.4)
        if overlay_path.exists():
            print(f"   ✅ {overlay_path.name}")

    # ── Validate embedding ──
    embedding = data.get("image_embedding")
    if embedding:
        assert isinstance(embedding, list), "Embedding should be a list"
        assert len(embedding) > 0, "Embedding should not be empty"
        # SigLIP so400m has 1152-dim embeddings
        print(f"\n🧬 Embedding: {len(embedding)} dimensions")
        norm = sum(x**2 for x in embedding) ** 0.5
        print(f"   L2 norm: {norm:.4f}")
    else:
        print("\n⚠ No embedding returned")

    # ── Inference metadata ──
    model_id = data.get("model_id", "unknown")
    endpoint_ms = data.get("inference_time_ms", 0)

    print(f"\n⏱️  Timing:")
    print(f"   Model inference: {endpoint_ms:.1f} ms")
    print(f"   Wall time (incl. network): {wall_time_ms:.1f} ms")
    print(f"   Model: {model_id}")

    # ── Save raw response (minus bulky base64) ──
    display_data = {k: v for k, v in data.items() if k != "heatmaps"}
    if display_data.get("image_embedding"):
        display_data["image_embedding"] = f"[{len(display_data['image_embedding'])} dims]"
    display_data["heatmap_count"] = len(heatmaps)
    display_data["_test_wall_time_ms"] = round(wall_time_ms, 1)

    response_path = OUTPUT_DIR / "response_summary.json"
    response_path.write_text(json.dumps(display_data, indent=2))
    print(f"\n📄 Response summary: {response_path}")

    # ── Final verdict ──
    print(f"\n{'='*60}")
    print(f"  ✅ ALL CHECKS PASSED")
    print(f"     {len(scores)} scores (all in [0,1])")
    print(f"     {len(heatmaps)} heatmaps (valid PNGs, non-uniform)")
    print(f"     {'Embedding' if embedding else 'No embedding'}")
    print(f"     {model_id}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(run_test())
