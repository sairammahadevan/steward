"""Tests for document parsing."""
import hashlib
from pathlib import Path
import pytest
from src.doc_parser import (
    DocType,
    ParsedDocument,
    compute_sha256,
    parse_text_content,
    _parse_text,
)


def test_compute_sha256(tmp_path):
    f = tmp_path / "test.txt"
    f.write_bytes(b"hello world")
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert compute_sha256(f) == expected


def test_parse_text_content_basic():
    result = parse_text_content("Water filter bought on Jan 2024", "my-note")
    assert result.doc_type == DocType.TEXT
    assert result.success
    assert "Water filter" in result.text
    assert result.filename == "my-note"
    assert len(result.sha256) == 64


def test_parse_text_content_dedup():
    r1 = parse_text_content("same content", "title1")
    r2 = parse_text_content("same content", "title2")
    assert r1.sha256 == r2.sha256


def test_parse_text_content_empty_title():
    result = parse_text_content("some text", "")
    assert result.filename == "pasted-text"


def test_parse_text_file(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("This is a test document about my TV warranty.", encoding="utf-8")
    result = _parse_text(f, f.name, compute_sha256(f))
    assert result.success
    assert result.doc_type == DocType.TEXT
    assert "warranty" in result.text


def test_parse_unsupported_extension(tmp_path):
    from src.doc_parser import parse_document
    f = tmp_path / "file.xyz"
    f.write_bytes(b"data")
    result = parse_document(f)
    assert not result.success
    assert "Unsupported" in result.error


def test_parsed_document_is_vision_false():
    doc = ParsedDocument(doc_type=DocType.TEXT_PDF, sha256="abc", filename="f.pdf", text="hello")
    assert not doc.is_vision


def test_parsed_document_is_vision_true():
    doc = ParsedDocument(doc_type=DocType.SCANNED_PDF, sha256="abc", filename="f.pdf",
                         image_paths=[Path("/tmp/page0.png")])
    assert doc.is_vision
