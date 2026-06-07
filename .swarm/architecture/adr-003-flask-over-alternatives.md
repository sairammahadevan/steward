# ADR-003: Use Flask Over Streamlit or FastAPI

## Status
Accepted

## Context
Sage started with Streamlit then migrated to Flask. RAG Control Plane used FastAPI
with a separate Streamlit frontend. Both created friction — Streamlit's execution
model caused state management issues; FastAPI + Streamlit as two separate processes
added operational complexity for a personal tool.

## Decision
Use Flask with Jinja2 templates for the entire UI layer.

Single process, single port, simple `bash run.sh`. No separate frontend server.
No React, no Vue, no JavaScript build step.

## Consequences
**Good:**
- Single command to run the entire application
- Proven in Sage — Sairam is already familiar with the setup
- Jinja2 templates are simple to read and modify
- No JavaScript framework complexity
- Fast to build UI pages

**Bad:**
- Not a "modern" SPA — full page reloads on form submit
- No real-time updates without polling or websockets (not needed for MVP)
- Less interactive than React-based alternatives

**Neutral:**
- Can add HTMX later for partial page updates if needed without a full rewrite
