"""Modal deployment — Google HeAR (Health Acoustic Representations).

Serves the audio analysis endpoint for respiratory/health sounds.
GPU: T4 (16 GB) — HeAR is a lightweight embedding model (~400M params).

Deploy:  modal deploy deploy/modal/hear_audio.py
Test:    modal run deploy/modal/hear_audio.py
Logs:    modal app logs medai-hear-audio
"""

from __future__ import annotations

import modal

# ── Modal resources ────────────────────────────────────────

app = modal.App("medai-hear-audio")

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
    )
)


# ── Model class ────────────────────────────────────────────

@app.cls(
    image=image,
    gpu="T4",
    timeout=300,
    scaledown_window=900,  # Keep warm for 15 min after last request
    secrets=[modal.Secret.from_name("huggingface-secret")],
    volumes={"/root/.cache/huggingface": hf_cache},
)
class HeARAudio:
    """Google HeAR — Health Acoustic Representations.

    Produces 512-dim embeddings from 2-second audio clips,
    then classifies them into health-relevant categories.
    """

    model_id: str = "google/hear-pytorch"
    sample_rate: int = 16000
    clip_duration: float = 2.0  # seconds
    clip_samples: int = 32000   # 2s × 16kHz

    @modal.enter()
    def load_model(self):
        """Load HeAR model on container startup."""
        import torch
        from transformers import AutoModel

        self.model = AutoModel.from_pretrained(self.model_id)
        self.model.eval()

        # Move to GPU if available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(self.device)

        hf_cache.commit()
        print(f"✅ HeAR loaded on {self.device}")

    def _preprocess_audio(self, audio_array, sr: int):
        """Convert raw audio to 2-second clips at 16kHz and compute spectrograms.

        HeAR expects mel-spectrogram input. We follow the
        preprocessing from the official HeAR repository.
        """
        import numpy as np
        import torch
        import librosa

        # Resample to 16kHz if needed
        if sr != self.sample_rate:
            audio_array = librosa.resample(
                audio_array, orig_sr=sr, target_sr=self.sample_rate,
            )

        # Ensure mono
        if audio_array.ndim > 1:
            audio_array = np.mean(audio_array, axis=0)

        # Split into 2-second clips (pad last clip if needed)
        clips = []
        for start in range(0, len(audio_array), self.clip_samples):
            clip = audio_array[start:start + self.clip_samples]
            if len(clip) < self.clip_samples:
                clip = np.pad(clip, (0, self.clip_samples - len(clip)))
            clips.append(clip)

        # Convert to mel spectrogram for each clip
        # HeAR uses 128 mel bands, 25ms window, 10ms hop
        spectrograms = []
        for clip in clips:
            mel = librosa.feature.melspectrogram(
                y=clip.astype(np.float32),
                sr=self.sample_rate,
                n_mels=128,
                n_fft=400,       # 25ms at 16kHz
                hop_length=160,  # 10ms at 16kHz
                fmin=60,
                fmax=7800,
            )
            log_mel = librosa.power_to_db(mel, ref=np.max)
            # Normalize to [-1, 1]
            log_mel = (log_mel - log_mel.mean()) / (log_mel.std() + 1e-8)
            spectrograms.append(log_mel)

        batch = np.stack(spectrograms, axis=0)
        return torch.from_numpy(batch).float().to(self.device), len(clips)

    def _classify_embedding(self, embedding):
        """Simple heuristic classifier on the embedding.

        In production, you'd fine-tune a classification head on
        labeled data. For the hackathon, we use embedding norms
        and basic statistics as proxy features.
        """
        import numpy as np

        emb = embedding.cpu().numpy()
        norm = float(np.linalg.norm(emb))
        mean = float(np.mean(emb))
        std = float(np.std(emb))

        # Heuristic classification based on embedding statistics
        # This is a placeholder — real classification requires fine-tuning
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

    @modal.fastapi_endpoint(method="POST", docs=True)
    def predict(self, request: dict) -> dict:
        """Analyze health audio and return classified segments.

        Request body:
            audio_url: str         — URL to audio file (WAV/MP3/FLAC)
            audio_type: str        — Expected type (breathing, cough, lung_sounds)
            clinical_context: str  — Clinical context

        Returns structured audio analysis as JSON.
        """
        import io
        import traceback

        import httpx
        import librosa
        import numpy as np
        import torch

        try:
            audio_url = request.get("audio_url", "")
            audio_type = request.get("audio_type", "breathing")
            clinical_context = request.get("clinical_context", "")

            # ── Download audio ─────────────────────────────
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(audio_url)
                resp.raise_for_status()

            # Load audio with librosa
            audio_data, sr = librosa.load(
                io.BytesIO(resp.content),
                sr=self.sample_rate,
                mono=True,
            )

            # ── Preprocess into clips ──────────────────────
            spectrograms, n_clips = self._preprocess_audio(audio_data, sr)

            # ── Get embeddings ─────────────────────────────
            with torch.inference_mode():
                # HeAR expects spectrograms as input
                # The exact input format depends on the model variant
                outputs = self.model(spectrograms, return_dict=True, output_hidden_states=True)

                # Use the last hidden state, mean-pooled
                if hasattr(outputs, "last_hidden_state"):
                    embeddings = outputs.last_hidden_state.mean(dim=1)
                elif hasattr(outputs, "pooler_output"):
                    embeddings = outputs.pooler_output
                else:
                    # Fallback — use the raw output
                    embeddings = outputs[0].mean(dim=1) if outputs[0].ndim == 3 else outputs[0]

            # ── Classify each segment ──────────────────────
            segments = []
            abnormal_timestamps = []
            clip_duration = self.clip_duration

            for i in range(n_clips):
                classification, confidence = self._classify_embedding(embeddings[i])

                time_start = i * clip_duration
                time_end = min((i + 1) * clip_duration, len(audio_data) / self.sample_rate)

                segments.append({
                    "time_start": round(time_start, 2),
                    "time_end": round(time_end, 2),
                    "classification": classification,
                    "confidence": round(confidence, 3),
                })

                if classification != "normal":
                    abnormal_timestamps.append(round(time_start, 2))

            # ── Build summary ──────────────────────────────
            abnormal_count = sum(1 for s in segments if s["classification"] != "normal")
            total_duration = round(len(audio_data) / self.sample_rate, 1)

            if abnormal_count == 0:
                summary = f"Normal {audio_type} sounds across {total_duration}s recording. No abnormalities detected."
            else:
                abnormal_types = list(set(s["classification"] for s in segments if s["classification"] != "normal"))
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


# ── Local test entrypoint ──────────────────────────────────

@app.local_entrypoint()
def main():
    """Quick smoke test with a sample audio URL."""
    model = HeARAudio()

    # Test with a publicly available breathing sound sample
    result = model.predict.remote({
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/4/4c/Stridulous_breathing.ogg",
        "audio_type": "breathing",
        "clinical_context": "Patient with suspected upper airway obstruction. Evaluate breathing sounds.",
    })
    import json
    print(json.dumps(result, indent=2))
