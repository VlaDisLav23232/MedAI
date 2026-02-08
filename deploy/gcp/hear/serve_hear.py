"""GCP Cloud Run — HeAR Audio Analysis Server.

Standalone FastAPI server that replicates the Modal HeAR deployment.
Analyzes health/respiratory audio and returns classified segments.

Model: google/hear-pytorch
GPU:   NVIDIA T4 (16 GB) — uses ~1 GB VRAM

The backend calls POST {HEAR_ENDPOINT} with JSON body (no path suffix),
so the main endpoint is mounted at POST /.
"""

from __future__ import annotations

import io
import os
import traceback

import httpx
import librosa
import numpy as np
import torch
import uvicorn
from fastapi import FastAPI

# ── App ────────────────────────────────────────────────────

app = FastAPI(title="HeAR Audio Analysis", version="1.0.0")

MODEL_ID = "google/hear-pytorch"
SAMPLE_RATE = 16000
CLIP_DURATION = 2.0       # seconds
CLIP_SAMPLES = 32000      # 2s × 16kHz

model = None
device = None


def load_model():
    global model, device
    from transformers import AutoModel

    hf_token = os.environ.get("HF_TOKEN", "")

    print(f"Loading {MODEL_ID} ...")
    model = AutoModel.from_pretrained(MODEL_ID, token=hf_token or None)
    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    print(f"✅ HeAR loaded on {device}")


@app.on_event("startup")
async def startup():
    load_model()


# ── Audio preprocessing ───────────────────────────────────

def _preprocess_audio(audio_array: np.ndarray, sr: int):
    """Convert raw audio to 2-second clips at 16kHz and compute mel spectrograms."""
    # Resample to 16kHz if needed
    if sr != SAMPLE_RATE:
        audio_array = librosa.resample(audio_array, orig_sr=sr, target_sr=SAMPLE_RATE)

    # Ensure mono
    if audio_array.ndim > 1:
        audio_array = np.mean(audio_array, axis=0)

    # Split into 2-second clips (pad last clip if needed)
    clips = []
    for start in range(0, len(audio_array), CLIP_SAMPLES):
        clip = audio_array[start : start + CLIP_SAMPLES]
        if len(clip) < CLIP_SAMPLES:
            clip = np.pad(clip, (0, CLIP_SAMPLES - len(clip)))
        clips.append(clip)

    # Compute mel spectrograms per clip
    spectrograms = []
    for clip in clips:
        mel = librosa.feature.melspectrogram(
            y=clip.astype(np.float32),
            sr=SAMPLE_RATE,
            n_mels=128,
            n_fft=400,       # 25ms at 16kHz
            hop_length=160,  # 10ms at 16kHz
            fmin=60,
            fmax=7800,
        )
        log_mel = librosa.power_to_db(mel, ref=np.max)
        log_mel = (log_mel - log_mel.mean()) / (log_mel.std() + 1e-8)
        spectrograms.append(log_mel)

    batch = np.stack(spectrograms, axis=0)
    return torch.from_numpy(batch).float().to(device), len(clips)


def _classify_embedding(embedding: torch.Tensor):
    """Heuristic classifier on HeAR embedding (placeholder — real use needs fine-tuning)."""
    emb = embedding.cpu().numpy()
    norm = float(np.linalg.norm(emb))
    std = float(np.std(emb))

    if norm > 20.0:
        classification = "abnormal_respiratory"
        confidence = min(0.85, norm / 30.0)
    elif std > 1.5:
        classification = "wheeze"
        confidence = min(0.75, std / 2.5)
    else:
        classification = "normal"
        confidence = 0.8

    return classification, confidence


# ── Main endpoint (POST /) ─────────────────────────────────

@app.post("/")
async def predict(request: dict) -> dict:
    """Analyze health audio and return classified segments.

    Request body (matches Modal contract):
        audio_url: str         — URL to audio file (WAV/MP3/FLAC/OGG)
        audio_type: str        — Expected type (breathing, cough, lung_sounds)
        clinical_context: str  — Clinical context

    Returns:
        audio_type, segments, summary, abnormal_segment_timestamps,
        embedding_id, total_duration_seconds, n_clips_analyzed
    """
    try:
        audio_url = request.get("audio_url", "")
        audio_type = request.get("audio_type", "breathing")
        clinical_context = request.get("clinical_context", "")

        # ── Download audio ─────────────────────────────────
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(audio_url)
            resp.raise_for_status()

        # Load audio with librosa
        audio_data, sr = librosa.load(
            io.BytesIO(resp.content),
            sr=SAMPLE_RATE,
            mono=True,
        )

        # ── Preprocess into clips ──────────────────────────
        spectrograms, n_clips = _preprocess_audio(audio_data, sr)

        # ── Get embeddings ─────────────────────────────────
        with torch.inference_mode():
            outputs = model(spectrograms, return_dict=True, output_hidden_states=True)

            if hasattr(outputs, "last_hidden_state"):
                embeddings = outputs.last_hidden_state.mean(dim=1)
            elif hasattr(outputs, "pooler_output"):
                embeddings = outputs.pooler_output
            else:
                embeddings = outputs[0].mean(dim=1) if outputs[0].ndim == 3 else outputs[0]

        # ── Classify each segment ──────────────────────────
        segments = []
        abnormal_timestamps = []

        for i in range(n_clips):
            classification, confidence = _classify_embedding(embeddings[i])

            time_start = i * CLIP_DURATION
            time_end = min((i + 1) * CLIP_DURATION, len(audio_data) / SAMPLE_RATE)

            segments.append({
                "time_start": round(time_start, 2),
                "time_end": round(time_end, 2),
                "classification": classification,
                "confidence": round(confidence, 3),
            })

            if classification != "normal":
                abnormal_timestamps.append(round(time_start, 2))

        # ── Build summary ──────────────────────────────────
        abnormal_count = sum(1 for s in segments if s["classification"] != "normal")
        total_duration = round(len(audio_data) / SAMPLE_RATE, 1)

        if abnormal_count == 0:
            summary = (
                f"Normal {audio_type} sounds across {total_duration}s recording. "
                "No abnormalities detected."
            )
        else:
            abnormal_types = list(
                set(s["classification"] for s in segments if s["classification"] != "normal")
            )
            summary = (
                f"Detected {abnormal_count}/{n_clips} abnormal segments "
                f"({', '.join(abnormal_types)}) in {total_duration}s {audio_type} recording."
            )

        return {
            "audio_type": audio_type,
            "segments": segments,
            "summary": summary,
            "abnormal_segment_timestamps": abnormal_timestamps,
            "embedding_id": f"emb-hear-{n_clips}clips",
            "total_duration_seconds": total_duration,
            "n_clips_analyzed": n_clips,
        }

    except Exception as e:
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "audio_type": request.get("audio_type", "unknown"),
            "segments": [],
            "summary": f"Error during audio analysis: {e}",
        }


# ── Health check ───────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_id": MODEL_ID,
        "gpu": torch.cuda.get_device_name() if torch.cuda.is_available() else "cpu",
    }


# ── Entry point ────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
