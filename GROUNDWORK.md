# STEWARD — Groundwork Document

**Your personal home document manager and life admin alert system.**

> Drop in your documents. Ask anything. Get reminded before things expire.

---

## The Problem

Life admin is invisible until it breaks. Water filter AMC lapses. Bike service
gets missed. A warranty you need is in a drawer somewhere. Legal documents have
answers you can't find.

STEWARD solves two things:

1. **Retrieval** — ask any question about any document you've stored
2. **Alerts** — be reminded before something expires or is due, via WhatsApp

---

## What STEWARD Is Not

- Not a RAG system (no vector embeddings, no chunking pipeline)
- Not a general knowledge base (that's Sage — different problem)
- Not a cloud service (your files never permanently leave your machine)

---

## Core Architecture Decision

**Claude API (Anthropic) over local LLMs.**

Local models (Gemma 3B, Ollama) are underpowered for reliable extraction from
legal documents and scanned images on an M3 8GB machine. Claude API is used
instead with the following privacy posture:

- Document text transits Anthropic's servers only during ingestion and queries
- Inputs/outputs deleted within 7 days by default
- Never used for model training
- Actual document files stay on your machine permanently
- Cost at personal scale: negligible (< ₹500/year estimated)

This is an accepted tradeoff. See ADR-001.

---

## Architecture Overview

```
YOUR MACHINE                          ANTHROPIC API
─────────────────────────────         ──────────────────────
Your Documents (PDF/scan/DOCX)  ──►  Claude reads, extracts
         │                            structured card, returns
         ▼                       ◄──  (text deleted ≤7 days)
   SQLite Database
   (metadata index)
         │
    ┌────┴──────┐
    │           │
  Query       Scheduler
  Engine      (daily)
    │           │
  Answer     WhatsApp
  in UI      Alert
```

**What lives locally forever:** document files, SQLite DB, application code
**What transits Anthropic briefly:** document text during ingestion/query

---

## The SQLite Card

Every ingested document produces one structured record:

```
item            Water Filter
type            AMC
purchase_date   2024-03-15
next_due_date   2025-03-15
doc_path        /Users/sairam/docs/water-filter-amc.pdf
doc_type        scanned_image | text_pdf | docx
notes           Annual maintenance, Kent service center
tags            home, appliance, maintenance
created_at      2026-06-07
```

This is the index. The actual document file stays where you put it.

---

## Agent Swarm

STEWARD is built by a swarm of 5 specialised agents. Each owns a domain.
No agent touches another agent's files.

### 🎯 Product Owner
Owns the vision, priorities, and MVP gate decisions.
Files owned: `.swarm/board/`

### 🏛️ Architect
Owns system design, technology decisions, and ADRs.
Files owned: `.swarm/architecture/`, `pyproject.toml`, `Makefile`

### ⚙️ Backend Developer
Owns all Python logic — ingestion, extraction, SQLite, Claude client,
scheduler, and alert delivery.
Files owned: `src/` (non-UI)

### 🎨 Frontend Developer
Owns the Flask UI — upload, ask, dashboard, document list.
Files owned: `src/ui/`

### 🔍 QA Agent
Owns all tests and phase gate reviews.
Files owned: `tests/`, `.swarm/reviews/`

---

## MVP Breakdown

### MVP 1 — "Drop it in, see the card"
**Goal:** Upload a document, Claude extracts the metadata card, it appears in SQLite and is visible in the UI.

Acceptance criteria:
- [ ] Upload PDF (text) → card created in SQLite
- [ ] Upload PDF (scanned image) → Claude reads visually, card created
- [ ] Upload DOCX → card created
- [ ] Paste text → card created
- [ ] UI shows list of all ingested documents with their cards
- [ ] Duplicate upload detected (SHA-256), not re-ingested
- [ ] Works offline for UI browsing (only ingestion needs internet)

Out of scope for MVP 1: querying, alerts, WhatsApp

---

### MVP 2 — "Ask anything"
**Goal:** Ask a question, STEWARD finds the right document, Claude answers from it.

Acceptance criteria:
- [ ] Type a question in UI → answer returned
- [ ] Answer cites which document it came from
- [ ] Scanned documents answerable (vision path works)
- [ ] "I don't know" response when no document has the answer
- [ ] Multi-document questions work (e.g. "what appliances do I own?")

Out of scope for MVP 2: alerts, WhatsApp

---

### MVP 3 — "Remind me before it's too late"
**Goal:** Scheduler runs daily, surfaces upcoming due dates, sends WhatsApp alert.

Acceptance criteria:
- [ ] Scheduler runs daily (configurable time)
- [ ] Items due within 30 days surface as alerts
- [ ] WhatsApp message sent via Twilio
- [ ] Alert format: "🔔 STEWARD: Your [item] [type] is due on [date] — [X days away]"
- [ ] No duplicate alerts for same item on same day
- [ ] Configurable alert window (7 / 15 / 30 days)

---

## Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Language | Python 3.11+ | Consistency with Sage |
| LLM | Claude API (Anthropic) | Privacy + quality + cost |
| Document parsing | pymupdf | Text extraction + image conversion |
| Database | SQLite (via sqlite3) | Local, zero-ops, sufficient for personal scale |
| Web UI | Flask + Jinja2 | Proven in Sage, simple |
| Scheduler | APScheduler | Lightweight local scheduler, no separate process |
| WhatsApp | Twilio API | Reliable, simple SDK |
| Testing | pytest | Consistency with Sage |
| Linting | ruff | Consistency with Sage |

---

## Project Structure (target)

```
steward/
├── src/
│   ├── config.py              # Settings from .env
│   ├── claude_client.py       # Anthropic API wrapper
│   ├── extractor.py           # Document → structured card
│   ├── doc_parser.py          # PDF/DOCX → text or images
│   ├── database.py            # SQLite read/write
│   ├── query_engine.py        # Question → find doc → ask Claude
│   ├── scheduler.py           # APScheduler + alert logic
│   ├── alerter.py             # Twilio / WhatsApp delivery
│   └── ui/
│       ├── flask_app.py       # Routes
│       ├── templates/         # Jinja2 HTML
│       └── static/            # CSS
├── tests/
├── docs/                      # User documents (gitignored)
├── .swarm/
│   ├── agents/                # Agent role definitions
│   ├── architecture/          # ADRs
│   ├── board/                 # Backlog, sprint, done
│   ├── requirements/          # Phase specs
│   └── reviews/               # QA gate reviews
├── .env.example
├── .gitignore
├── Makefile
├── pyproject.toml
└── run.sh
```

---

## What We Build First

MVP 1 only. Nothing else gets touched until MVP 1 passes QA gate.

Order within MVP 1:
1. Architect writes ADRs and project scaffold spec
2. Backend Dev builds Claude client + doc parser + extractor + SQLite
3. Frontend Dev builds upload UI and document list
4. QA writes tests and runs gate review
5. Product Owner approves → MVP 1 ships

---

## Name Rationale

**STEWARD** — a person who manages a household's affairs, documents, and schedules.
Exactly what this system does. No acronym needed.

---

_Document version: 1.0 — June 2026_
_Status: Pre-build groundwork — no code written yet_
