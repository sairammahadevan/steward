# STEWARD Product Backlog

_Maintained by: 🎯 Product Owner_
_Last updated: 2026-06-07_

---

## MVP 1 — "Drop it in, see the card"
**Goal:** Upload a document → Claude extracts metadata → card stored in SQLite → visible in UI.

| ID | Story | Owner | Priority |
|----|-------|-------|----------|
| M1-1 | Project scaffold, config, Claude client | Architect + Backend | 🔴 NOW |
| M1-2 | Document parser (text PDF, scanned PDF, DOCX) | Backend | 🔴 NOW |
| M1-3 | Metadata extractor (Claude extracts structured card) | Backend | 🔴 NOW |
| M1-4 | SQLite database layer (insert, query, dedup) | Backend | 🔴 NOW |
| M1-5 | Flask UI — upload page + document list | Frontend | 🔴 NOW |
| M1-6 | Tests + QA gate review | QA | 🔴 NOW |

---

## MVP 2 — "Ask anything"
**Goal:** Ask a question → right document found → Claude answers from it.

| ID | Story | Priority |
|----|-------|----------|
| M2-1 | Query engine — match question to document via SQLite | 🟡 NEXT |
| M2-2 | Claude Q&A — send doc + question, return cited answer | 🟡 NEXT |
| M2-3 | Flask UI — Ask page | 🟡 NEXT |
| M2-4 | Multi-document questions ("what appliances do I own?") | 🟡 NEXT |
| M2-5 | Tests + QA gate review | 🟡 NEXT |

---

## MVP 3 — "Remind me before it's too late"
**Goal:** Daily scheduler checks due dates → WhatsApp alert fired automatically.

| ID | Story | Priority |
|----|-------|----------|
| M3-1 | Scheduler (APScheduler, daily job) | 🟢 LATER |
| M3-2 | Due-date checker — items due within configurable window | 🟢 LATER |
| M3-3 | Twilio / WhatsApp alerter | 🟢 LATER |
| M3-4 | Dashboard — upcoming due dates visible in UI | 🟢 LATER |
| M3-5 | No-duplicate-alert logic | 🟢 LATER |
| M3-6 | Tests + QA gate review | 🟢 LATER |

---

## Icebox
- Semantic search with embeddings (if collection grows large)
- Email alert as fallback to WhatsApp
- Bulk import from a folder
- Document categories / folders in UI
- Export cards to CSV
