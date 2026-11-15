# Manhattan Dermatology Lead Enrichment

Pipeline that sources Manhattan dermatology practices from the NPPES NPI Registry,

deduplicates them, enriches from practice websites, scores confidence, and ranks fit for Dr.Tracker.

## Setup

uv venv --python 3.12 .venv && source .venv/bin/activate

uv pip install -r requirements.txt

ollama pull qwen2.5:7b