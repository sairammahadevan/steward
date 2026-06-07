"""Tests for the query engine."""
import pytest
from src.query_engine import _find_relevant, _format_card, Answer
from src.database import DocumentRow


def _make_row(item="Water Filter", type="AMC", tags=None, notes="", filename="wf.pdf",
              sha256="abc", next_due_date=None):
    return DocumentRow(
        id=1, sha256=sha256, filename=filename, doc_path="/tmp/wf.pdf",
        doc_type="text_pdf", item=item, type=type,
        purchase_date="2024-01-01", next_due_date=next_due_date,
        notes=notes, tags=tags or ["home"], created_at="2026-06-07",
    )


# ── _find_relevant ────────────────────────────────────────────────────────────

def test_find_relevant_keyword_match():
    docs = [
        _make_row(item="Water Filter", sha256="a"),
        _make_row(item="Property Tax", sha256="b", filename="tax.pdf"),
    ]
    result = _find_relevant("water filter expiry", docs)
    assert len(result) == 1
    assert result[0].item == "Water Filter"


def test_find_relevant_broad_returns_all():
    docs = [_make_row(sha256="a"), _make_row(sha256="b", filename="b.pdf")]
    result = _find_relevant("list all my documents", docs)
    assert len(result) == 2


def test_find_relevant_no_match_returns_empty():
    docs = [_make_row(item="Water Filter", sha256="a")]
    result = _find_relevant("motorcycle insurance", docs)
    assert result == []


def test_find_relevant_tag_match():
    docs = [_make_row(tags=["vehicle", "bike"], sha256="a")]
    result = _find_relevant("bike service", docs)
    assert len(result) == 1


def test_find_relevant_notes_match():
    docs = [_make_row(notes="Honda Activa purchased in 2023", sha256="a")]
    result = _find_relevant("honda maintenance", docs)
    assert len(result) == 1


# ── _format_card ─────────────────────────────────────────────────────────────

def test_format_card_all_fields():
    row = _make_row(next_due_date="2025-01-01")
    text = _format_card(row)
    assert "Water Filter" in text
    assert "AMC" in text
    assert "2025-01-01" in text


def test_format_card_null_fields():
    row = _make_row()
    row.purchase_date = None
    row.next_due_date = None
    text = _format_card(row)
    assert "Not found" in text


# ── answer_question (unit — no Claude call) ───────────────────────────────────

def test_answer_question_empty_vault(monkeypatch):
    from src import query_engine
    monkeypatch.setattr(query_engine, "get_all_documents", lambda: [])
    result = query_engine.answer_question("What do I own?")
    assert not result.found
    assert "empty" in result.text.lower()
