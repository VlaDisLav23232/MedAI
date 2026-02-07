# MedAI Backend

Agentic Medical AI Assistant — Backend API

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Copy env file and add your Anthropic API key
cp .env.example .env

# Run in debug mode (uses mock tools, no GPU needed)
DEBUG=true uvicorn medai.main:app --reload

# Run tests
pytest -m unit -v
```
