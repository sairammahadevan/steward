"""Tests for the SQLite database layer."""
import pytest
from pathlib import Path
from src import database
from src.extractor import DocumentCard


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Redirect database to a temp file for each test."""
    db_path = tmp_path / "test_steward.db"
    monkeypatch.setattr(database.settings, "db_path", db_path)
    database.init_db()
    yield db_path


def _make_card(sha256="abc123", filename="test.pdf", item="Water Filter"):
    return DocumentCard(
        filename=filename,
        sha256=sha256,
        doc_type="text_pdf",
        doc_path="/tmp/test.pdf",
        item=item,
        type="AMC",
        purchase_date="2024-01-15",
        next_due_date="2025-01-15",
        notes="Annual maintenance",
        tags=["home", "appliance"],
    )


def test_init_db_creates_table(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    monkeypatch.setattr(database.settings, "db_path", db_path)
    database.init_db()
    assert db_path.exists()


def test_document_not_exists_initially():
    assert not database.document_exists("nonexistent-sha")


def test_insert_and_exists():
    card = _make_card()
    database.insert_document(card)
    assert database.document_exists("abc123")


def test_insert_returns_id():
    card = _make_card()
    row_id = database.insert_document(card)
    assert isinstance(row_id, int)
    assert row_id > 0


def test_get_all_documents_empty():
    assert database.get_all_documents() == []


def test_get_all_documents_returns_inserted():
    card = _make_card()
    database.insert_document(card)
    docs = database.get_all_documents()
    assert len(docs) == 1
    assert docs[0].item == "Water Filter"
    assert docs[0].type == "AMC"
    assert docs[0].tags == ["home", "appliance"]


def test_get_document_by_id():
    card = _make_card()
    row_id = database.insert_document(card)
    doc = database.get_document_by_id(row_id)
    assert doc is not None
    assert doc.sha256 == "abc123"


def test_get_document_by_id_not_found():
    assert database.get_document_by_id(9999) is None


def test_count_documents():
    assert database.count_documents() == 0
    database.insert_document(_make_card(sha256="a1"))
    database.insert_document(_make_card(sha256="a2", filename="b.pdf"))
    assert database.count_documents() == 2


def test_null_fields_stored_correctly():
    card = DocumentCard(
        filename="minimal.pdf",
        sha256="min123",
        doc_type="text_pdf",
        doc_path="/tmp/minimal.pdf",
    )
    database.insert_document(card)
    docs = database.get_all_documents()
    assert docs[0].item is None
    assert docs[0].next_due_date is None
    assert docs[0].tags == []


def test_due_within_days(monkeypatch):
    import datetime
    # Card due tomorrow
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    card = _make_card(sha256="due1")
    card.next_due_date = tomorrow
    database.insert_document(card)

    # Card due in 60 days
    future = (datetime.date.today() + datetime.timedelta(days=60)).isoformat()
    card2 = _make_card(sha256="due2", filename="far.pdf")
    card2.next_due_date = future
    database.insert_document(card2)

    within_30 = database.get_documents_due_within_days(30)
    assert len(within_30) == 1
    assert within_30[0].sha256 == "due1"
