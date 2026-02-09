"""Whisper-based transcription route.

POST /api/v1/transcribe
Accepts audio as base64-encoded WAV, transcribes with OpenAI Whisper locally,
and returns the text.  Used by the frontend voice button.
"""

from __future__ import annotations

import base64
import io
import tempfile
import time

import numpy as np
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter(tags=["transcription"])

# ── Lazy-loaded Whisper model (loaded once on first request) ──

_whisper_model = None


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        logger.info("loading_whisper_model", model_size="base")
        import whisper

        _whisper_model = whisper.load_model("base")
        logger.info("whisper_model_loaded")
    return _whisper_model


# ── Schemas ───────────────────────────────────────────────────

class TranscribeRequest(BaseModel):
    audio_base64: str
    language: str = "en"


class TranscribeResponse(BaseModel):
    transcription: str
    duration_seconds: float
    error: str | None = None


# ── Route ─────────────────────────────────────────────────────

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(req: TranscribeRequest):
    """Transcribe base64-encoded audio using Whisper."""
    try:
        # Decode base64 → raw bytes
        raw_b64 = req.audio_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        audio_bytes = base64.b64decode(raw_b64)

        # Decode WAV → float32 numpy array
        from scipy.io import wavfile as scipy_wav

        buf = io.BytesIO(audio_bytes)
        try:
            sr, data = scipy_wav.read(buf)
        except Exception:
            # Fallback: assume raw 16-bit PCM at 16kHz
            sr = 16000
            data = np.frombuffer(audio_bytes, dtype=np.int16)

        # Convert to float32
        if data.dtype == np.int16:
            audio = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            audio = data.astype(np.float32) / 2_147_483_648.0
        else:
            audio = data.astype(np.float32)

        # Mono
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        # Resample to 16kHz if needed (Whisper expects 16kHz)
        if sr != 16000:
            from scipy import signal as scipy_signal
            import math

            gcd = math.gcd(sr, 16000)
            audio = scipy_signal.resample_poly(audio, 16000 // gcd, sr // gcd).astype(np.float32)

        duration = len(audio) / 16000.0
        logger.info("transcribe_request", duration_s=round(duration, 1), sr=sr)

        # Transcribe with Whisper
        model = _get_model()
        t0 = time.time()

        # Write to temp file since whisper.transcribe accepts path or ndarray
        result = model.transcribe(audio, language=req.language, fp16=False)
        elapsed = time.time() - t0

        text = result.get("text", "").strip()
        logger.info(
            "transcribe_complete",
            text_len=len(text),
            elapsed_ms=round(elapsed * 1000),
        )

        return TranscribeResponse(
            transcription=text,
            duration_seconds=round(duration, 2),
        )

    except Exception as exc:
        logger.error("transcribe_error", error=str(exc))
        return TranscribeResponse(
            transcription="",
            duration_seconds=0.0,
            error=str(exc),
        )
