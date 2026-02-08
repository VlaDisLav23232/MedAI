# Agentic-MedAI-SoftServe
Source code repository for the AgentForge hackathon by SoftServe

~/medai-run.sh --mode mock
~/medai-run.sh --mode real
~/medai-run.sh --mode fast
~/medai-run.sh --mode fastest --backend-port 8001 --frontend-port 3001
~/medai-stop.sh

mock: DEBUG=true, judge off, 27B off
real: DEBUG=false, judge on, 27B on
fast: DEBUG=false, judge off, 27B on
fastest: DEBUG=false, judge off, 27B off
