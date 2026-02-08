"""Modal deployment — MedGemma 4B IT (Multimodal).

Serves the image + text analysis endpoint.
GPU: A10G (24 GB) — MedGemma 4B at bf16 uses ~10-12 GB VRAM.

Deploy:  modal deploy deploy/modal/medgemma_4b.py
Test:    modal run deploy/modal/medgemma_4b.py
Logs:    modal app logs medai-medgemma-4b
"""

from __future__ import annotations

import modal

# ── Modal resources ────────────────────────────────────────

app = modal.App("medai-medgemma-4b")

# Persistent volume to cache model weights (avoid re-downloading)
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
    )
)


# ── Model class ────────────────────────────────────────────

@app.cls(
    image=image,
    gpu="A10G",
    timeout=600,
    scaledown_window=900,  # Keep warm for 15 min after last request
    secrets=[modal.Secret.from_name("huggingface-secret")],
    volumes={"/root/.cache/huggingface": hf_cache},
)
class MedGemma4B:
    """MedGemma 4B IT — multimodal medical image + text analysis."""

    model_id: str = "google/medgemma-4b-it"

    @modal.enter()
    def load_model(self):
        """Load model on container startup (cached in volume)."""
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = AutoModelForImageTextToText.from_pretrained(
            self.model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )
        self.model.eval()

        # Commit the downloaded weights to the volume for caching
        hf_cache.commit()

        print(f"✅ {self.model_id} loaded on {torch.cuda.get_device_name()}")

    @modal.fastapi_endpoint(method="POST", docs=True)
    def predict(self, request: dict) -> dict:
        """Analyze a medical image with optional clinical context.

        Request body:
            image_url: str       — URL of the medical image
            clinical_context: str — Doctor's question / symptoms
            modality_hint: str   — Expected modality (xray, ct, mri, etc.)

        Returns structured findings as JSON.
        """
        import io
        import json
        import traceback

        import httpx
        import torch
        from PIL import Image

        try:
            image_url = request.get("image_url", "")
            clinical_context = request.get("clinical_context", "Describe this medical image in detail.")
            modality_hint = request.get("modality_hint", "")

            # ── Build the prompt ───────────────────────────
            system_prompt = (
                "You are an expert radiologist and medical imaging specialist. "
                "Analyze the provided medical image and return a JSON response with the following structure:\n"
                '{"modality_detected": "<xray|ct|mri|ultrasound|fundus|dermatology|histopathology|other>",\n'
                ' "findings": [{"finding": "<description>", "confidence": <0.0-1.0>, '
                '"explanation": "<detailed clinical explanation>", "severity": "<none|mild|moderate|severe|critical>"}],\n'
                ' "differential_diagnoses": ["<diagnosis1>", ...],\n'
                ' "recommended_followup": ["<action1>", ...]}\n'
                "\nIMPORTANT RULES:\n"
                "- confidence is your self-assessed certainty about each finding (NOT a calibrated probability).\n"
                "- Be conservative: only report findings you can clearly identify in the image.\n"
                "- Return ONLY valid JSON, no markdown formatting or code fences."
            )

            user_text = clinical_context
            if modality_hint:
                user_text += f"\n\nExpected modality: {modality_hint}"

            # ── Download and process image ─────────────────
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                img_response = client.get(image_url)
                img_response.raise_for_status()

            image = Image.open(io.BytesIO(img_response.content)).convert("RGB")

            # ── Build messages ─────────────────────────────
            messages = [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": user_text},
                    ],
                },
            ]

            # ── Inference ──────────────────────────────────
            import time as _time

            inputs = self.processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            ).to(self.model.device, dtype=torch.bfloat16)

            _t0 = _time.monotonic()
            with torch.inference_mode():
                output = self.model.generate(
                    **inputs,
                    max_new_tokens=1024,
                    do_sample=False,
                    pad_token_id=self.processor.tokenizer.eos_token_id,
                    return_dict_in_generate=True,
                    output_scores=True,
                )
            inference_time_ms = round((_time.monotonic() - _t0) * 1000, 1)

            # Decode only the generated tokens
            output_ids = output.sequences
            generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
            raw_text = self.processor.decode(generated_ids, skip_special_tokens=True)
            token_count = len(generated_ids)

            # ── Compute logprob-based confidence ───────────
            # Real confidence from token-level log-probabilities:
            # For each generated token, take the log-prob of the chosen token,
            # then compute the geometric mean probability across the sequence.
            import math
            logprob_confidence = None
            if output.scores:
                log_probs = []
                for i, score in enumerate(output.scores):
                    if i >= len(generated_ids):
                        break
                    token_id = generated_ids[i].item()
                    # score shape: [batch_size, vocab_size]
                    token_logprob = torch.log_softmax(score[0], dim=-1)[token_id].item()
                    log_probs.append(token_logprob)
                if log_probs:
                    # Geometric mean probability = exp(mean of log-probs)
                    mean_logprob = sum(log_probs) / len(log_probs)
                    logprob_confidence = round(math.exp(mean_logprob), 4)

            # ── Parse response ─────────────────────────────
            # Try to extract JSON from the response
            try:
                # Strip markdown code fences if present
                cleaned = raw_text.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                    cleaned = cleaned.rsplit("```", 1)[0]
                result = json.loads(cleaned)
            except json.JSONDecodeError:
                # Model didn't return valid JSON — wrap in structured format
                result = {
                    "modality_detected": modality_hint or "other",
                    "findings": [
                        {
                            "finding": raw_text[:500],
                            "confidence": 0.5,
                            "explanation": "Raw model output (JSON parsing failed)",
                            "severity": "none",
                        }
                    ],
                    "differential_diagnoses": [],
                    "recommended_followup": [],
                    "raw_output": raw_text,
                }

            # Inject real logprob-based confidence into the response
            if logprob_confidence is not None:
                result["logprob_confidence"] = logprob_confidence
                # Also set per-finding confidence to logprob if model's self-reported was used
                for finding in result.get("findings", []):
                    finding["model_self_reported_confidence"] = finding.get("confidence", 0.5)
                    finding["logprob_confidence"] = logprob_confidence

            # Inject real inference metadata
            result["inference"] = {
                "model_id": self.model_id,
                "temperature": 0.0,  # do_sample=False → greedy decoding
                "token_count": token_count,
                "inference_time_ms": inference_time_ms,
                "sequence_fluency_score": logprob_confidence,
            }

            return result

        except Exception as e:
            return {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "modality_detected": "other",
                "findings": [],
            }


# ── Local test entrypoint ──────────────────────────────────

@app.local_entrypoint()
def main():
    """Quick smoke test — call the deployed model."""
    model = MedGemma4B()
    result = model.predict.remote({
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/c/c8/Chest_Xray_PA_3-8-2010.png",
        "clinical_context": "Patient presents with persistent cough for 3 weeks and low-grade fever. Evaluate chest X-ray.",
        "modality_hint": "xray",
    })
    import json
    print(json.dumps(result, indent=2))
