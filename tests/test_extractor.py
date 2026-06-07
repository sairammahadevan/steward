"""Tests for the metadata extractor."""
import pytest
from src.extractor import _parse_response, _date_or_none, _str_or_none, _tags, DocumentCard
from src.doc_parser import ParsedDocument, DocType


def _make_parsed(text="Water filter AMC doc", filename="wf.pdf", sha256="abc"):
    return ParsedDocument(doc_type=DocType.TEXT, sha256=sha256, filename=filename, text=text)


# ── Unit tests for helpers ────────────────────────────────────────────────────

def test_date_or_none_valid():
    assert _date_or_none("2024-03-15") == "2024-03-15"


def test_date_or_none_invalid():
    assert _date_or_none("March 2024") is None
    assert _date_or_none(None) is None
    assert _date_or_none("null") is None


def test_str_or_none_empty():
    assert _str_or_none("") is None
    assert _str_or_none(None) is None
    assert _str_or_none("null") is None


def test_str_or_none_truncates():
    assert len(_str_or_none("x" * 600, max_len=300)) == 300


def test_tags_filters_and_limits():
    result = _tags(["Home", "APPLIANCE", "maintenance", "water", "filter", "extra"])
    assert len(result) == 5
    assert all(t == t.lower() for t in result)


def test_tags_non_list():
    assert _tags("not a list") == []
    assert _tags(None) == []


# ── Parse response tests ──────────────────────────────────────────────────────

def test_parse_response_valid_json():
    raw = '{"item": "Water Filter", "type": "AMC", "purchase_date": "2024-01-15", "next_due_date": "2025-01-15", "notes": "Annual maintenance", "tags": ["home"]}'
    parsed = _make_parsed()
    card = _parse_response(raw, parsed, "/tmp/wf.pdf")
    assert card.success
    assert card.item == "Water Filter"
    assert card.type == "AMC"
    assert card.purchase_date == "2024-01-15"
    assert card.next_due_date == "2025-01-15"
    assert "home" in card.tags


def test_parse_response_strips_markdown_fence():
    raw = '```json\n{"item": "Bike", "type": "Service", "purchase_date": null, "next_due_date": "2025-06-01", "notes": "", "tags": ["vehicle"]}\n```'
    parsed = _make_parsed()
    card = _parse_response(raw, parsed, "/tmp/bike.pdf")
    assert card.success
    assert card.item == "Bike"


def test_parse_response_invalid_json():
    raw = "Here is some explanation: not JSON at all."
    parsed = _make_parsed()
    card = _parse_response(raw, parsed, "/tmp/wf.pdf")
    assert not card.success
    assert "JSON" in card.extraction_error


def test_parse_response_null_fields():
    raw = '{"item": null, "type": null, "purchase_date": null, "next_due_date": null, "notes": null, "tags": []}'
    parsed = _make_parsed()
    card = _parse_response(raw, parsed, "/tmp/wf.pdf")
    assert card.success
    assert card.item is None
    assert card.next_due_date is None
    assert card.tags == []


def test_extract_fails_gracefully_on_bad_parsed():
    from src.extractor import extract
    bad = ParsedDocument(doc_type=DocType.TEXT, sha256="x", filename="x.pdf", error="parse failed")
    result = extract(bad, "/tmp/x.pdf")
    assert not result.success
    assert "parse failed" in result.error
