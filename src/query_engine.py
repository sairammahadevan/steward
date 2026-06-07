"""
Query engine for STEWARD — MVP 2.

Pipeline:
1. Get all document cards from SQLite
2. Find relevant documents via keyword matching
3. Load full text for relevant docs (re-parse from file)
4. Send context + question to Claude (sonnet)
5. Return cited answer

For broad questions ("what do I own?"), all cards are used.
For specific questions ("what's my property tax amount?"), only matching docs are loaded.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.claude_client import ClaudeClient
from src.config import settings
from src.database import DocumentRow, get_all_documents

logger = logging.getLogger(__name__)

# Words that signal a broad "tell me everything" query
BROAD_QUERY_SIGNALS = {
    "all", "every", "list", "what do i own", "what have i", "show me",
    "summarise", "summarize", "overview", "everything",
}

SYSTEM_PROMPT_TEMPLATE = """You are STEWARD, a personal assistant for a home document vault.
Answer questions using ONLY the documents provided below.
Always mention which document your answer comes from.
If the answer is not in the documents, say clearly: "I don't have that information in your vault."
Be concise and specific. For follow-up questions, remember the full conversation so far.

DOCUMENTS IN VAULT:
{context}"""


@dataclass
class Answer:
    """Result of a query."""
    question: str
    text: str
    sources: list[str] = field(default_factory=list)
    found: bool = True
    error: str = ""


def answer_question(
    question: str,
    history: Optional[list[dict]] = None,
) -> Answer:
    """
    Answer a question about the user's documents, with optional conversation history.

    Args:
        question: The current user question.
        history:  List of previous {role, content} dicts (Claude message format).
                  Pass the full prior conversation for multi-turn support.

    Returns:
        Answer with text and source citations.
    """
    all_docs = get_all_documents()

    if not all_docs:
        return Answer(
            question=question,
            text="Your vault is empty. Upload some documents first.",
            found=False,
        )

    # Decide which docs are relevant to the question
    relevant = _find_relevant(question, all_docs)
    if not relevant:
        relevant = all_docs  # broad question → use all

    # Build document context
    context_parts: list[str] = []
    sources: list[str] = []

    for doc in relevant:
        card_text = _format_card(doc)
        full_text = _load_doc_text(doc)
        if full_text:
            context_parts.append(
                f"=== {doc.filename} ===\n{card_text}\n\nFull content:\n{full_text[:8000]}"
            )
        else:
            context_parts.append(f"=== {doc.filename} ===\n{card_text}")
        sources.append(doc.filename)

    context = "\n\n".join(context_parts)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    # Build messages: prior history + current question
    messages: list[dict] = list(history or [])
    messages.append({"role": "user", "content": question})

    try:
        client = ClaudeClient()
        response = client.generate_chat(
            messages,
            system_prompt=system_prompt,
            model=settings.query_model,
            max_tokens=1024,
        )
    except Exception as e:
        logger.error("Claude query failed: %s", e)
        return Answer(question=question, text="", found=False, error=str(e))

    return Answer(
        question=question,
        text=response.text.strip(),
        sources=sources,
        found=True,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_relevant(question: str, docs: list[DocumentRow]) -> list[DocumentRow]:
    """
    Find documents relevant to the question via keyword matching.
    Returns all docs if the question is broad, or a filtered list if specific.
    """
    q_lower = question.lower()
    q_words = set(q_lower.split())

    # Broad query — return everything
    if q_words & BROAD_QUERY_SIGNALS:
        return docs

    matched = []
    for doc in docs:
        score = 0
        searchable = " ".join(filter(None, [
            doc.item or "",
            doc.type or "",
            doc.filename,
            doc.notes or "",
            " ".join(doc.tags),
        ])).lower()

        for word in q_words:
            if len(word) > 2 and word in searchable:
                score += 1

        if score > 0:
            matched.append((score, doc))

    matched.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in matched] if matched else []


def _format_card(doc: DocumentRow) -> str:
    """Format a document card as readable text for Claude."""
    lines = [
        f"Item: {doc.item or 'Unknown'}",
        f"Type: {doc.type or 'Unknown'}",
        f"Purchase date: {doc.purchase_date or 'Not found'}",
        f"Next due date: {doc.next_due_date or 'Not found'}",
        f"Tags: {', '.join(doc.tags) if doc.tags else 'None'}",
        f"Notes: {doc.notes or 'None'}",
    ]
    return "\n".join(lines)


def _load_doc_text(doc: DocumentRow) -> str:
    """
    Try to load full text from the original document file.
    Returns empty string if file not found or parsing fails.
    """
    if doc.doc_path == "pasted-text":
        return ""

    path = Path(doc.doc_path)
    if not path.exists():
        logger.warning("Document file not found: %s", doc.doc_path)
        return ""

    try:
        from src.doc_parser import parse_document
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            parsed = parse_document(path, tmp_dir=Path(tmp))
        return parsed.text if parsed.text else ""
    except Exception as e:
        logger.warning("Could not load doc text for %s: %s", doc.filename, e)
        return ""
