# ADR-004: Use PyMuPDF for Document Parsing

## Status
Accepted

## Context
STEWARD must handle three document types: text PDFs, scanned image PDFs, and DOCX files.
The parser must detect whether a PDF has selectable text (text PDF) or is purely
image-based (scanned), and route accordingly — text extraction for the former,
image conversion for the latter (to be sent to Claude's vision API).

## Decision
Use `pymupdf` (also importable as `fitz`) as the primary document parsing library.

- Text PDFs: extract text directly via `page.get_text()`
- Scanned PDFs: detect via `page.get_text() == ""`, convert pages to images via `page.get_pixmap()`
- DOCX: use `python-docx` for text extraction (pymupdf does not handle DOCX well)

Detection logic: if a PDF page yields fewer than 50 characters of text, treat it
as a scanned page and send as image to Claude vision.

## Consequences
**Good:**
- pymupdf is fast and reliable for both text extraction and image rendering
- Single library handles the text vs. scanned detection problem
- Already present in RAG Control Plane dependencies — Sairam has used it before
- Image quality from `get_pixmap()` is sufficient for Claude vision at 150dpi

**Bad:**
- pymupdf has a commercial license (AGPL) — acceptable for personal use
- Image conversion for large PDFs generates significant data to send to Claude (cost consideration)

**Neutral:**
- Mixed PDFs (some text pages, some scanned) handled page by page
- DOCX requires a second library (python-docx) — acceptable, small footprint
