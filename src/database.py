"""
SQLite database layer for STEWARD.

Single table: documents
One row per ingested document — the metadata card.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256            TEXT UNIQUE NOT NULL,
    filename          TEXT NOT NULL,
    doc_path          TEXT NOT NULL,
    doc_type          TEXT NOT NULL,
    item              TEXT,
    type              TEXT,
    purchase_date     TEXT,
    next_due_date     TEXT,
    notes             TEXT,
    tags              TEXT,
    created_at        TEXT NOT NULL,
    status            TEXT DEFAULT 'active',
    file_size_bytes   INTEGER DEFAULT 0,
    input_tokens      INTEGER DEFAULT 0,
    output_tokens     INTEGER DEFAULT 0
);
"""


@dataclass
class DocumentRow:
    """A row from the documents table."""
    id: int
    sha256: str
    filename: str
    doc_path: str
    doc_type: str
    item: Optional[str]
    type: Optional[str]
    purchase_date: Optional[str]
    next_due_date: Optional[str]
    notes: Optional[str]
    tags: list[str]
    created_at: str
    status: str = "active"       # "active" | "done"
    file_size_bytes: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


def _connect() -> sqlite3.Connection:
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    with _connect() as conn:
        conn.execute(CREATE_TABLE_SQL)
        # Safe migrations: add new columns if missing (existing DBs won't have them)
        for migration in [
            "ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'active'",
            "ALTER TABLE documents ADD COLUMN file_size_bytes INTEGER DEFAULT 0",
            "ALTER TABLE documents ADD COLUMN input_tokens INTEGER DEFAULT 0",
            "ALTER TABLE documents ADD COLUMN output_tokens INTEGER DEFAULT 0",
        ]:
            try:
                conn.execute(migration)
            except sqlite3.OperationalError:
                pass  # column already exists
        conn.commit()
    logger.debug("Database initialised at %s", settings.db_path)


def document_exists(sha256: str) -> bool:
    """Return True if a document with this SHA-256 is already in the database."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM documents WHERE sha256 = ?", (sha256,)
        ).fetchone()
    return row is not None


def insert_document(card) -> int:
    """
    Insert a DocumentCard into the database.

    Args:
        card: DocumentCard from extractor.py

    Returns:
        The new row's id.
    """
    from src.extractor import DocumentCard
    assert isinstance(card, DocumentCard)

    tags_json = json.dumps(card.tags)
    created_at = datetime.now().isoformat()

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents
                (sha256, filename, doc_path, doc_type, item, type,
                 purchase_date, next_due_date, notes, tags, created_at,
                 file_size_bytes, input_tokens, output_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card.sha256,
                card.filename,
                card.doc_path,
                card.doc_type,
                card.item,
                card.type,
                card.purchase_date,
                card.next_due_date,
                card.notes,
                tags_json,
                created_at,
                getattr(card, "file_size_bytes", 0),
                getattr(card, "input_tokens", 0),
                getattr(card, "output_tokens", 0),
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid

    logger.info("Saved document card: id=%d filename=%s", row_id, card.filename)
    return row_id


def delete_document(doc_id: int) -> None:
    """Permanently delete a document record from the DB (file on disk is kept)."""
    with _connect() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
    logger.info("Deleted document record id=%d", doc_id)


def update_document_status(doc_id: int, status: str) -> None:
    """Toggle a document's status between 'active' and 'done'."""
    assert status in ("active", "done")
    with _connect() as conn:
        conn.execute("UPDATE documents SET status = ? WHERE id = ?", (status, doc_id))
        conn.commit()
    logger.info("Document %d status → %s", doc_id, status)


def get_all_documents() -> list[DocumentRow]:
    """Return all documents, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM documents ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_dataclass(r) for r in rows]


def get_document_by_id(doc_id: int) -> Optional[DocumentRow]:
    """Return a single document by id, or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return _row_to_dataclass(row) if row else None


def get_documents_due_within_days(days: int) -> list[DocumentRow]:
    """
    Return documents whose next_due_date falls within the next N days.
    Used by the scheduler.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM documents
            WHERE next_due_date IS NOT NULL
              AND next_due_date >= ?
              AND next_due_date <= date(?, '+' || ? || ' days')
            ORDER BY next_due_date ASC
            """,
            (today, today, days),
        ).fetchall()
    return [_row_to_dataclass(r) for r in rows]


def count_documents() -> int:
    """Return total number of documents in the database."""
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]


def _row_to_dataclass(row: sqlite3.Row) -> DocumentRow:
    tags_raw = row["tags"]
    try:
        tags = json.loads(tags_raw) if tags_raw else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    return DocumentRow(
        id=row["id"],
        sha256=row["sha256"],
        filename=row["filename"],
        doc_path=row["doc_path"],
        doc_type=row["doc_type"],
        item=row["item"],
        type=row["type"],
        purchase_date=row["purchase_date"],
        next_due_date=row["next_due_date"],
        notes=row["notes"],
        tags=tags,
        created_at=row["created_at"],
        status=row["status"] if row["status"] else "active",
        file_size_bytes=row["file_size_bytes"] or 0,
        input_tokens=row["input_tokens"] or 0,
        output_tokens=row["output_tokens"] or 0,
    )
