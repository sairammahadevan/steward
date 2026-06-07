# ADR-001: Use Claude API (Anthropic) Over Local LLMs

## Status
Accepted

## Context
The predecessor attempt (RAG Control Plane + Sage) used local models via Ollama
(Gemma 3B, Llama variants). On an Apple M3 with 8GB RAM, the system consistently
ran out of memory, crashed mid-inference, and produced poor extraction quality
from legal documents and scanned images. 3B parameter models are insufficient
for reliable structured data extraction from dense or handwritten documents.

The user's primary concern is privacy — personal documents including legal deeds,
warranties, and service records should not be used for AI training.

## Decision
Use the Anthropic Claude API as the sole LLM provider.

Model: `claude-haiku-4-5` for ingestion (fast, cheap, sufficient for extraction).
Model: `claude-sonnet-4-6` for query answering (better reasoning for complex questions).
Both configurable via `.env`.

Privacy posture accepted by user:
- Document text transits Anthropic's servers during API calls
- Inputs/outputs deleted within 7 days by default
- Never used for model training (API tier guarantee)
- Actual document files remain on local machine permanently

## Consequences
**Good:**
- Reliable extraction quality including from scanned images (vision support)
- No local GPU/CPU load — M3 stays cool
- 200K token context window — handles large legal documents in one call
- Cost at personal scale is negligible (< ₹500/year estimated)
- Single SDK dependency replaces Ollama + Docker + model management

**Bad:**
- Requires internet connection — no offline ingestion
- Document text leaves the machine briefly during API calls
- Subject to Anthropic rate limits and API availability
- Requires API key and billing setup

**Neutral:**
- Model can be swapped in `.env` without code changes
- Cost scales with usage but personal scale is minimal
