# MVP 1 Requirements — Ingestion + SQLite Index

_Owner: 🎯 Product Owner_
_Phase: MVP 1_
_Goal: Upload a document → Claude extracts metadata → card stored in SQLite → visible in UI_

---

## User Story

As Sairam, I want to upload any personal document (warranty, legal deed, AMC receipt,
service record) and have STEWARD automatically extract the key information and store
it in a local index — so I have a single place to see all my documents and what they
contain, without having to open each file manually.

---

## Functional Requirements

### FR-1: Document Ingestion
The system must accept the following input methods:
- File upload via UI (PDF, DOCX)
- Paste plain text via UI with an optional title

### FR-2: Document Type Detection
The parser must detect and route correctly:
- **Text PDF** — has selectable text → extract text directly
- **Scanned PDF** — image-based pages → convert to images for Claude vision
- **Mixed PDF** — some text pages, some scanned → handle page by page
- **DOCX** — extract text via python-docx

Detection rule: if a PDF page yields < 50 characters, treat as scanned.

### FR-3: Metadata Extraction
Claude must extract and return a structured card for every document:

```
item            (str) Name of the item/asset — e.g. "Water Filter", "House"
type            (str) Category — AMC | Warranty | Legal | Service | Insurance | Other
purchase_date   (str | null) ISO date or null if not found
next_due_date   (str | null) ISO date of next service/expiry/renewal or null
notes           (str) Any other useful info from the document (max 300 chars)
tags            (list[str]) 2-5 keyword tags — e.g. ["home", "appliance", "maintenance"]
```

If a field cannot be extracted with confidence, it must be null — not hallucinated.

### FR-4: Duplicate Detection
Before processing, compute SHA-256 hash of the file content.
If the hash already exists in SQLite, skip processing and inform the user.

### FR-5: SQLite Storage
Each successfully processed document produces one row in the `documents` table:

```sql
CREATE TABLE documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256        TEXT UNIQUE NOT NULL,
    filename      TEXT NOT NULL,
    doc_path      TEXT NOT NULL,
    doc_type      TEXT NOT NULL,         -- text_pdf | scanned_pdf | docx | text
    item          TEXT,
    type          TEXT,
    purchase_date TEXT,
    next_due_date TEXT,
    notes         TEXT,
    tags          TEXT,                  -- JSON array stored as string
    created_at    TEXT NOT NULL          -- ISO datetime
);
```

### FR-6: Document List UI
The `/documents` page must show all ingested documents as cards, displaying:
- Filename
- Item name and type
- Purchase date and next due date (or "Not found" if null)
- Tags
- Notes preview (first 100 chars)

### FR-7: Upload UI
The `/ingest` page must allow:
- File drag-and-drop or click-to-upload (PDF, DOCX)
- Text paste with optional title field
- Clear success/error feedback after each upload
- Show processing state while Claude is working

---

## Non-Functional Requirements

### NFR-1: Privacy
- Uploaded files stored locally in `docs/` folder (gitignored)
- Only extracted text/images sent to Claude API, not the file itself
- No logging of document content — only filenames and processing status

### NFR-2: Error Handling
- Claude API failure → show error, do not create partial card
- Unsupported file type → reject with clear message
- File > 50MB → reject with clear message
- Corrupt PDF → handle gracefully, show error

### NFR-3: Performance
- Text PDF ingestion < 15 seconds
- Scanned PDF ingestion < 30 seconds per page (Claude vision is slower)
- UI remains responsive during processing (no browser freeze)

---

## Extraction Prompt (seed — Backend Dev to refine)

```
You are a document analyst. Extract structured information from the following document.

Return your response as JSON with exactly these fields:
{
  "item": "name of the item or asset this document is about",
  "type": "one of: AMC | Warranty | Legal | Service | Insurance | Other",
  "purchase_date": "YYYY-MM-DD or null",
  "next_due_date": "YYYY-MM-DD or null",
  "notes": "any other useful information, max 300 characters",
  "tags": ["tag1", "tag2"]
}

Rules:
- If you cannot find a field with confidence, use null — do not guess
- Dates must be in YYYY-MM-DD format
- next_due_date is the date of the next required action (service, expiry, renewal)
- tags should be 2-5 lowercase keywords
- notes should capture anything useful that doesn't fit other fields

Document:
{document_text_or_images}
```

---

## Out of Scope for MVP 1
- Question answering (MVP 2)
- WhatsApp alerts (MVP 3)
- Editing or deleting cards
- Batch import
- Search within the document list

---

## Acceptance Criteria for Gate

- [ ] Text PDF upload → card in SQLite ✓
- [ ] Scanned PDF upload → card in SQLite via vision ✓
- [ ] DOCX upload → card in SQLite ✓
- [ ] Text paste → card in SQLite ✓
- [ ] Duplicate file rejected with message ✓
- [ ] Document list shows all cards with correct fields ✓
- [ ] Null fields shown gracefully (not as "None" or crashes) ✓
- [ ] All pytest tests passing ✓
- [ ] No hardcoded API keys ✓
- [ ] `bash run.sh` starts the app ✓
- [ ] App handles Claude API failure without crashing ✓
