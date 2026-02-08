"""Modal deployment — MedASR (Medical Automatic Speech Recognition).

Serves medical dictation transcription via CTC-based ASR.
Optimised for radiology and clinical dictation.

Model: google/medasr  (~1.1 GB, lasr_ctc architecture)
GPU:   T4 (16 GB) — uses ~2 GB VRAM at fp32

Deploy:  modal deploy deploy/modal/medasr.py
Test:    modal run deploy/modal/medasr.py
Logs:    modal app logs medai-medasr
"""

from __future__ import annotations

import modal

# ── Modal resources ────────────────────────────────────────

app = modal.App("medai-medasr")

hf_cache = modal.Volume.from_name("medai-hf-cache", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(
        "torch>=2.5.0",
        "transformers>=4.50.0",
        "librosa>=0.10.0",
        "soundfile>=0.12.0",
        "numpy>=1.26.0",
        "pydantic>=2.10.0",
        "fastapi>=0.115.0",
        "httpx>=0.28.0",
        "sentencepiece>=0.2.0",
    )
)


# ── Model class ────────────────────────────────────────────

@app.cls(
    image=image,
    gpu="T4",
    timeout=300,
    scaledown_window=900,
    secrets=[modal.Secret.from_name("huggingface-secret")],
    volumes={"/root/.cache/huggingface": hf_cache},
)
class MedASR:
    """Google MedASR — Medical Automatic Speech Recognition.

    CTC-based model fine-tuned for radiology / clinical dictation.
    Accepts audio (URL or base64) and returns transcription text.
    """

    model_id: str = "google/medasr"
    target_sr: int = 16000

    @modal.enter()
    def load_model(self):
        """Load model on container startup."""
        import torch
        from transformers import AutoFeatureExtractor, AutoModelForCTC, AutoTokenizer

        self.feature_extractor = AutoFeatureExtractor.from_pretrained(self.model_id)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForCTC.from_pretrained(self.model_id)
        self.model.eval()

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(self.device)

        hf_cache.commit()
        print(f"✅ MedASR loaded on {self.device}")

    @modal.fastapi_endpoint(method="POST", docs=True)
    def predict(self, request: dict) -> dict:
        """Transcribe medical audio to text.

        Request body:
            audio_url: str       — URL to audio file (WAV/MP3/FLAC/OGG)
            audio_base64: str    — Base64-encoded audio bytes (alternative)
            language: str        — Language hint (default: "en")

        Returns:
            transcription: str   — The transcribed text
            duration_seconds: float
            model_id: str
        """
        import base64
        import io
        import re
        import time
        import traceback

        import httpx
        import librosa
        import numpy as np
        import torch

        try:
            audio_url = request.get("audio_url", "")
            audio_b64 = request.get("audio_base64", "")

            if not audio_url and not audio_b64:
                return {"error": "audio_url or audio_base64 is required"}

            # ── Load audio ─────────────────────────────────
            if audio_b64:
                if "," in audio_b64:
                    audio_b64 = audio_b64.split(",", 1)[1]
                audio_bytes = base64.b64decode(audio_b64)
                waveform, sr = librosa.load(
                    io.BytesIO(audio_bytes), sr=self.target_sr, mono=True,
                )
            else:
                with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                    resp = client.get(audio_url)
                    resp.raise_for_status()
                waveform, sr = librosa.load(
                    io.BytesIO(resp.content), sr=self.target_sr, mono=True,
                )

            duration = len(waveform) / sr

            # ── Normalize audio ────────────────────────────
            rms = np.sqrt(np.mean(waveform ** 2))
            if rms > 0:
                waveform = waveform / rms
            waveform = np.clip(waveform, -1.0, 1.0)

            # ── Remove silence ─────────────────────────────
            energy = np.abs(waveform)
            above_threshold = energy > 0.01
            if np.any(above_threshold):
                start = max(0, np.where(above_threshold)[0][0] - int(0.1 * sr))
                end = min(len(waveform), np.where(above_threshold)[0][-1] + int(0.1 * sr))
                waveform = waveform[start:end]

            if len(waveform) / sr < 0.1:
                return {
                    "transcription": "",
                    "duration_seconds": round(duration, 2),
                    "model_id": self.model_id,
                    "warning": "Audio too short after silence removal",
                }

            # ── Feature extraction ─────────────────────────
            inputs = self.feature_extractor(
                waveform,
                sampling_rate=self.target_sr,
                return_tensors="pt",
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Find the main input tensor (input_features or input_values)
            input_tensor = None
            for key, val in inputs.items():
                if isinstance(val, torch.Tensor) and val.ndim > 1:
                    input_tensor = val
                    break

            if input_tensor is None:
                return {"error": "Could not extract audio features"}

            # ── Compute stride and max_length ──────────────
            stride = 4
            if hasattr(self.feature_extractor, "stride"):
                s = self.feature_extractor.stride
                stride = s[0] if isinstance(s, (list, tuple)) else s
            max_length = input_tensor.shape[1] // stride + 50

            # ── Inference ──────────────────────────────────
            t0 = time.monotonic()

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=8,
                    temperature=1.0,
                )

            transcription = self.tokenizer.batch_decode(
                outputs.tolist(), skip_special_tokens=True
            )[0]

            inference_ms = round((time.monotonic() - t0) * 1000, 1)

            # ── Post-process ───────────────────────────────
            transcription = re.sub(r"\s+", " ", transcription).strip()

            return {
                "transcription": transcription,
                "duration_seconds": round(duration, 2),
                "inference_time_ms": inference_ms,
                "model_id": self.model_id,
            }

        except Exception as e:
            return {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "transcription": "",
            }


# ── Local test entrypoint ──────────────────────────────────

@app.local_entrypoint()
def main():
    """Quick smoke test."""
    model = MedASR()
    result = model.predict.remote({
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/4/4c/Stridulous_breathing.ogg",
    })
    import json
    print(json.dumps(result, indent=2))
