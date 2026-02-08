"""Modal deployment — MedGemma 27B Text IT.

Serves the heavy clinical text reasoning endpoint.
GPU: A100-80GB at bf16 (or L40S with int4 quantization).

Deploy:  modal deploy deploy/modal/medgemma_27b.py
Test:    modal run deploy/modal/medgemma_27b.py
Logs:    modal app logs medai-medgemma-27b
"""

from __future__ import annotations

import modal

# ── Modal resources ────────────────────────────────────────

app = modal.App("medai-medgemma-27b")

hf_cache = modal.Volume.from_name("medai-hf-cache", create_if_missing=True)

# Use A100-80GB for bf16 (safest), fall back to H100 if A100 unavailable
# If you want to save cost, switch to int4 quantization on L40S
USE_QUANTIZATION = False  # Set True to use int4 on L40S instead

if USE_QUANTIZATION:
    GPU_TYPE = "L40S"
else:
    GPU_TYPE = "A100-80GB"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.5.0",
        "transformers>=4.50.0",
        "accelerate>=1.2.0",
        "pydantic>=2.10.0",
        "fastapi>=0.115.0",
        "sentencepiece>=0.2.0",
        # Quantization deps (only used if USE_QUANTIZATION=True)
        "bitsandbytes>=0.45.0",
    )
)


# ── Model class ────────────────────────────────────────────

@app.cls(
    image=image,
    gpu=GPU_TYPE,
    timeout=600,
    scaledown_window=900,  # Keep warm for 15 min after last request
    secrets=[modal.Secret.from_name("huggingface-secret")],
    volumes={"/root/.cache/huggingface": hf_cache},
)
class MedGemma27B:
    """MedGemma 27B Text IT — heavy clinical reasoning."""

    model_id: str = "google/medgemma-27b-text-it"

    @modal.enter()
    def load_model(self):
        """Load the 27B model on container startup."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        load_kwargs = {
            "torch_dtype": torch.bfloat16,
            "device_map": "auto",
        }

        if USE_QUANTIZATION:
            from transformers import BitsAndBytesConfig
            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_quant_type="nf4",
            )

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            **load_kwargs,
        )
        self.model.eval()
        hf_cache.commit()

        print(f"✅ {self.model_id} loaded ({'int4' if USE_QUANTIZATION else 'bf16'})")

    @modal.fastapi_endpoint(method="POST", docs=True)
    def predict(self, request: dict) -> dict:
        """Clinical text reasoning with structured JSON output.

        Request body:
            patient_history: str   — Full patient history
            lab_results: str       — Lab results text/JSON
            clinical_context: str  — Doctor's question
            imaging_findings: str  — Summary from image analysis

        Returns structured assessment as JSON.
        """
        import json
        import traceback

        import torch

        try:
            patient_history = request.get("patient_history", "")
            lab_results = request.get("lab_results", "")
            clinical_context = request.get("clinical_context", "")
            imaging_findings = request.get("imaging_findings", "")

            # ── Build prompt ───────────────────────────────
            system_prompt = (
                "You are an expert clinical reasoning physician. "
                "Analyze the provided patient information and return a JSON response with this structure:\n"
                '{"reasoning_chain": [{"step": 1, "thought": "<reasoning step>"}],\n'
                ' "assessment": "<clinical assessment>",\n'
                ' "confidence": <0.0-1.0>,\n'
                ' "evidence_citations": [{"source": "<src>", "source_type": "<type>", '
                '"relevant_excerpt": "<text>", "date": "<ISO date or null>"}],\n'
                ' "plan_suggestions": ["<suggestion1>", ...],\n'
                ' "contraindication_flags": ["<flag1>", ...]}\n'
                "Return ONLY valid JSON, no markdown formatting."
            )

            user_parts = []
            if patient_history:
                user_parts.append(f"**Patient History:**\n{patient_history}")
            if lab_results:
                user_parts.append(f"**Lab Results:**\n{lab_results}")
            if imaging_findings:
                user_parts.append(f"**Imaging Findings:**\n{imaging_findings}")
            user_parts.append(f"**Clinical Question:**\n{clinical_context}")

            user_text = "\n\n".join(user_parts)

            # ── Tokenize ───────────────────────────────────
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ]
            inputs = self.tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            )
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            # ── Inference ──────────────────────────────────
            import time as _time

            _t0 = _time.monotonic()
            with torch.inference_mode():
                output = self.model.generate(
                    **inputs,
                    max_new_tokens=2048,
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id,
                    return_dict_in_generate=True,
                    output_scores=True,
                )
            inference_time_ms = round((_time.monotonic() - _t0) * 1000, 1)

            output_ids = output.sequences
            generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
            raw_text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
            token_count = len(generated_ids)

            # ── Compute logprob-based confidence ───────────
            import math
            logprob_confidence = None
            if output.scores:
                log_probs = []
                for i, score in enumerate(output.scores):
                    if i >= len(generated_ids):
                        break
                    token_id = generated_ids[i].item()
                    token_logprob = torch.log_softmax(score[0], dim=-1)[token_id].item()
                    log_probs.append(token_logprob)
                if log_probs:
                    mean_logprob = sum(log_probs) / len(log_probs)
                    logprob_confidence = round(math.exp(mean_logprob), 4)

            # ── Parse response ─────────────────────────────
            try:
                cleaned = raw_text.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                    cleaned = cleaned.rsplit("```", 1)[0]
                result = json.loads(cleaned)
            except json.JSONDecodeError:
                result = {
                    "reasoning_chain": [{"step": 1, "thought": raw_text[:1000]}],
                    "assessment": raw_text[:500],
                    "confidence": 0.5,
                    "evidence_citations": [],
                    "plan_suggestions": [],
                    "contraindication_flags": [],
                    "raw_output": raw_text,
                }

            # Inject real logprob-based confidence
            if logprob_confidence is not None:
                result["model_self_reported_confidence"] = result.get("confidence", 0.5)
                result["logprob_confidence"] = logprob_confidence

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
                "reasoning_chain": [],
                "assessment": "Error during analysis",
                "confidence": 0.0,
            }


# ── Local test entrypoint ──────────────────────────────────

@app.local_entrypoint()
def main():
    """Quick smoke test."""
    model = MedGemma27B()
    result = model.predict.remote({
        "patient_history": (
            "52-year-old male, history of Type 2 DM (10 years), hypertension. "
            "Current medications: Metformin 1000mg BID, Lisinopril 20mg daily."
        ),
        "lab_results": "HbA1c: 8.2% (up from 6.8% 6 months ago). Fasting glucose: 185 mg/dL. Creatinine: 1.3 mg/dL.",
        "clinical_context": "Patient presents with worsening glycemic control despite medication adherence. Evaluate and suggest plan.",
        "imaging_findings": "",
    })
    import json
    print(json.dumps(result, indent=2))
