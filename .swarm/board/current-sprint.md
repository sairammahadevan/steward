# Current Sprint — MVP 1

_Started: 2026-06-07_
_Goal: Upload a document → Claude extracts metadata → card stored in SQLite → visible in UI_

---

## In Progress

| Task | Owner | Status |
|------|-------|--------|
| M1-1 — Scaffold + config + Claude client | Architect + Backend | 🔲 Not started |
| M1-2 — Document parser | Backend | 🔲 Not started |
| M1-3 — Metadata extractor | Backend | 🔲 Not started |
| M1-4 — SQLite database layer | Backend | 🔲 Not started |
| M1-5 — Flask UI (upload + doc list) | Frontend | 🔲 Not started |
| M1-6 — Tests + QA gate | QA | 🔲 Not started |

---

## MVP 1 Acceptance Criteria (gate checklist)

- [ ] Upload text PDF → card created in SQLite
- [ ] Upload scanned PDF → Claude reads visually → card created
- [ ] Upload DOCX → card created
- [ ] Paste text → card created
- [ ] Duplicate upload detected via SHA-256, not re-processed
- [ ] Document list page shows all cards
- [ ] Each card shows: item, type, purchase date, next due date, notes, tags
- [ ] All tests passing
- [ ] No hardcoded credentials
- [ ] App starts with `bash run.sh`

---

## Blocked
_Nothing blocked yet._

---

## Notes
- Start with M1-1 (scaffold) before any other task
- M1-5 (UI) can begin once M1-4 (database) interface is defined
- QA (M1-6) begins only after M1-1 through M1-5 are complete
