"""
Metadata extractor for STEWARD.

Sends parsed documents to Claude and extracts structured metadata cards.
Returns a DocumentCard dataclass ready to be saved to SQLite.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from src.claude_client import ClaudeClient
from src.config import settings
from src.doc_parser import ParsedDocument

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a document analyst for a personal home management system.
Extract structured information from the document provided.
Return ONLY valid JSON — no markdown, no explanation, just the JSON object."""

EXTRACTION_PROMPT = """Extract the key information from this document and return as JSON.

Return exactly this structure:
{{
  "item": "name of the item or asset (e.g. Water Filter, Honda Activa, Flat at Brigade)",
  "type": "one of: AMC | Warranty | Legal | Service | Insurance | Receipt | Other",
  "purchase_date": "YYYY-MM-DD or null",
  "next_due_date": "YYYY-MM-DD or null",
  "notes": "any other useful info, max 300 characters",
  "tags": ["tag1", "tag2"]
}}

Rules:
- If you cannot find a field with confidence, use null — never guess or hallucinate
- Dates must be in YYYY-MM-DD format
- next_due_date = the next required action date (service due, warranty expiry, AMC renewal)
- tags = 2-5 lowercase keywords describing the document
- notes = anything useful not captured in other fields

Document filename: {filename}

Document content:
{content}"""


@dataclass
class DocumentCard:
    """Structured metadata extracted from a document."""
    filename: str
    sha256: str
    doc_type: str
    doc_path: str
    item: Optional[str] = None
    type: Optional[str] = None
    purchase_date: Optional[str] = None
    next_due_date: Optional[str] = None
    notes: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    extraction_error: str = ""
    # Usage stats
    file_size_bytes: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def success(self) -> bool:
        return not self.extraction_error


@dataclass
class ExtractionResult:
    """Result of the extraction pipeline."""
    success: bool
    card: Optional[DocumentCard] = None
    error: str = ""


def extract(parsed: ParsedDocument, doc_path: str, file_size_bytes: int = 0) -> ExtractionResult:
    """
    Extract structured metadata from a parsed document using Claude.

    Args:
        parsed: ParsedDocument from doc_parser.
        doc_path: Absolute path string where the document is stored.

    Returns:
        ExtractionResult with a DocumentCard on success.
    """
    if not parsed.success:
        return ExtractionResult(success=False, error=parsed.error)

    try:
        client = ClaudeClient()
    except Exception as e:
        return ExtractionResult(success=False, error=str(e))

    try:
        if parsed.is_vision and parsed.image_paths:
            response = _extract_from_images(client, parsed)
        else:
            response = _extract_from_text(client, parsed)
    except Exception as e:
        logger.error("Claude extraction failed for %s: %s", parsed.filename, e)
        return ExtractionResult(success=False, error=f"Claude error: {e}")

    card = _parse_response(response.text, parsed, doc_path)
    card.input_tokens = response.input_tokens
    card.output_tokens = response.output_tokens
    card.file_size_bytes = file_size_bytes
    return ExtractionResult(success=card.success, card=card, error=card.extraction_error)


def _extract_from_text(client: ClaudeClient, parsed: ParsedDocument) -> str:
    """Extract from text content."""
    content = parsed.text[:60000]  # stay well within context limits
    prompt = EXTRACTION_PROMPT.format(filename=parsed.filename, content=content)
    return client.generate(prompt, system_prompt=SYSTEM_PROMPT)


def _extract_from_images(client: ClaudeClient, parsed: ParsedDocument) -> str:
    """Extract from scanned page images.

    Uses the query model (Sonnet) rather than the extraction model (Haiku)
    because vision / OCR reasoning is significantly better in Sonnet.
    """
    images = parsed.image_paths[:10]
    prompt = EXTRACTION_PROMPT.format(
        filename=parsed.filename,
        content="[Document provided as images above — use the visual content to extract metadata]",
    )
    # Sonnet has far superior vision capabilities for scanned documents
    return client.generate_with_images(
        prompt,
        image_paths=images,
        system_prompt=SYSTEM_PROMPT,
        model=settings.query_model,   # claude-sonnet-4-6 instead of haiku
    )


def _parse_response(raw: str, parsed: ParsedDocument, doc_path: str) -> DocumentCard:
    """Parse Claude's JSON response into a DocumentCard."""
    card = DocumentCard(
        filename=parsed.filename,
        sha256=parsed.sha256,
        doc_type=parsed.doc_type.value,
        doc_path=doc_path,
    )

    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse failed for %s: %s\nRaw: %s", parsed.filename, e, raw[:500])
        card.extraction_error = f"Could not parse Claude response as JSON: {e}"
        return card

    card.item = _str_or_none(data.get("item"))
    card.type = _str_or_none(data.get("type"))
    card.purchase_date = _date_or_none(data.get("purchase_date"))
    card.next_due_date = _date_or_none(data.get("next_due_date"))
    card.notes = _str_or_none(data.get("notes"), max_len=300)
    card.tags = _tags(data.get("tags"))

    logger.info(
        "Extracted card for %s: item=%s, type=%s, next_due=%s",
        parsed.filename, card.item, card.type, card.next_due_date,
    )
    return card


def _str_or_none(val: object, max_len: int = 500) -> Optional[str]:
    if val is None or val == "null":
        return None
    s = str(val).strip()
    return s[:max_len] if s else None


def _date_or_none(val: object) -> Optional[str]:
    """Validate and return a date string in YYYY-MM-DD format, or None."""
    if val is None or val == "null":
        return None
    s = str(val).strip()
    # Basic format check
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s
    return None


def _tags(val: object) -> list[str]:
    if not isinstance(val, list):
        return []
    return [str(t).lower().strip() for t in val if t][:5]
