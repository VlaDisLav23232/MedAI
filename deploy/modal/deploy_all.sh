#!/usr/bin/env bash
# ============================================================
#  MedAI — Deploy all Modal endpoints
#
#  Prerequisites:
#    1. modal setup          (authenticate CLI)
#    2. modal secret create huggingface-secret HF_TOKEN=hf_...
#    3. Accept model terms on HuggingFace (see README)
#
#  Usage:
#    bash deploy/modal/deploy_all.sh          # deploy all 3
#    bash deploy/modal/deploy_all.sh 4b       # deploy only 4B
#    bash deploy/modal/deploy_all.sh 27b      # deploy only 27B
#    bash deploy/modal/deploy_all.sh hear     # deploy only HeAR
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

deploy_4b() {
    echo "🚀 Deploying MedGemma 4B IT (image + text)..."
    modal deploy "$SCRIPT_DIR/medgemma_4b.py"
    echo "✅ MedGemma 4B deployed!"
    echo ""
}

deploy_27b() {
    echo "🚀 Deploying MedGemma 27B Text IT (clinical reasoning)..."
    modal deploy "$SCRIPT_DIR/medgemma_27b.py"
    echo "✅ MedGemma 27B deployed!"
    echo ""
}

deploy_hear() {
    echo "🚀 Deploying HeAR (audio analysis)..."
    modal deploy "$SCRIPT_DIR/hear_audio.py"
    echo "✅ HeAR deployed!"
    echo ""
}

deploy_siglip() {
    echo "🚀 Deploying SigLIP (image explainability)..."
    modal deploy "$SCRIPT_DIR/siglip_explainability.py"
    echo "✅ SigLIP deployed!"
    echo ""
}

deploy_medasr() {
    echo "🚀 Deploying MedASR (medical speech recognition)..."
    modal deploy "$SCRIPT_DIR/medasr.py"
    echo "✅ MedASR deployed!"
    echo ""
}

# Parse arguments
TARGET="${1:-all}"

case "$TARGET" in
    4b)     deploy_4b ;;
    27b)    deploy_27b ;;
    hear)   deploy_hear ;;
    siglip) deploy_siglip ;;
    medasr) deploy_medasr ;;
    all)
        deploy_4b
        deploy_27b
        deploy_hear
        deploy_siglip
        deploy_medasr
        echo "═══════════════════════════════════════════"
        echo "  All models deployed! 🎉"
        echo ""
        echo "  Check your endpoints at:"
        echo "    https://modal.com/apps"
        echo ""
        echo "  Copy the endpoint URLs into backend/.env:"
        echo "    MEDGEMMA_4B_ENDPOINT=https://your-username--medai-medgemma-4b-medgemma4b-predict.modal.run"
        echo "    MEDGEMMA_27B_ENDPOINT=https://your-username--medai-medgemma-27b-medgemma27b-predict.modal.run"
        echo "    HEAR_ENDPOINT=https://your-username--medai-hear-audio-hearaudio-predict.modal.run"
        echo "    MEDSIGLIP_ENDPOINT=https://your-username--medai-siglip-explainability-siglipexplainability-explain.modal.run"
        echo "    MEDASR_ENDPOINT=https://your-username--medai-medasr-medasr-predict.modal.run"
        echo "═══════════════════════════════════════════"
        ;;
    *)
        echo "Usage: $0 [4b|27b|hear|siglip|medasr|all]"
        exit 1
        ;;
esac
