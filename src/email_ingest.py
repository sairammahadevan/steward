"""
Email ingestion for STEWARD.

Polls a configured Gmail (or any IMAP) mailbox for unread emails with attachments.
Supported types: PDF, DOCX, DOC, TXT, MD.

Each attachment is saved to docs_dir and queued through the same background
pipeline used by the Upload page (IngestTracker + _process_file_job).

Typical flow:
  You email a PDF to your configured address
  → APScheduler calls poll_inbox() every N minutes
  → Attachment saved to docs/
  → Background thread runs Claude extraction
  → Document appears in STEWARD vault

Setup:
  Set STEWARD_EMAIL and STEWARD_EMAIL_PASSWORD (Gmail App Password) in .env
  Gmail App Passwords: myaccount.google.com/apppasswords
"""

from __future__ import annotations

import email
import imaplib
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from email.header import decode_header
from pathlib import Path
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}


@dataclass
class PollResult:
    """Summary of one inbox poll cycle."""
    checked_at: datetime = field(default_factory=datetime.now)
    emails_scanned: int = 0
    attachments_queued: int = 0
    error: str = ""

    @property
    def success(self) -> bool:
        return not self.error

    def checked_at_str(self) -> str:
        return self.checked_at.strftime("%H:%M:%S")


# Module-level state — in-memory, resets on restart (fine for local use)
_last_result: Optional[PollResult] = None
_result_lock = threading.Lock()


def get_last_result() -> Optional[PollResult]:
    with _result_lock:
        return _last_result


def poll_inbox() -> PollResult:
    """
    Connect to the configured IMAP mailbox, find UNSEEN emails with supported
    attachments, download and queue them for background extraction, then mark
    those emails as read.

    Returns a PollResult describing what happened.
    """
    global _last_result

    if not settings.steward_email or not settings.steward_email_password:
        result = PollResult(error="Email not configured")
        with _result_lock:
            _last_result = result
        return result

    result = PollResult()

    try:
        conn = imaplib.IMAP4_SSL(settings.email_imap_host, settings.email_imap_port)
        try:
            conn.login(settings.steward_email, settings.steward_email_password)
        except imaplib.IMAP4.error as e:
            result.error = f"Login failed — check STEWARD_EMAIL_PASSWORD: {e}"
            logger.error("IMAP login failed for %s: %s", settings.steward_email, e)
            with _result_lock:
                _last_result = result
            return result

        conn.select("INBOX")
        # Only pick up emails explicitly sent to STEWARD — subject must contain "STEWARD"
        _, data = conn.search(None, "UNSEEN", "SUBJECT", "STEWARD")
        msg_ids = [m for m in data[0].split() if m]
        result.emails_scanned = len(msg_ids)

        logger.info("Email poll: %d unseen STEWARD message(s) in %s", len(msg_ids), settings.steward_email)

        for msg_id in msg_ids:
            try:
                _, msg_data = conn.fetch(msg_id, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                subject = _decode_header_str(msg.get("Subject", "(no subject)"))
                logger.info("Processing email: %s", subject)

                queued = _process_message(msg)
                result.attachments_queued += queued

                if queued > 0:
                    # Mark as read only if we successfully queued something
                    conn.store(msg_id, "+FLAGS", "\\Seen")
                    logger.info("Marked message %s as read (%d attachment(s) queued)", msg_id, queued)

            except Exception as e:
                logger.warning("Error processing message %s: %s", msg_id, e)
                continue

        conn.logout()

    except imaplib.IMAP4.error as e:
        result.error = f"IMAP error: {e}"
        logger.error("Email poll IMAP error: %s", e)
    except OSError as e:
        result.error = f"Network error: {e}"
        logger.error("Email poll network error: %s", e)
    except Exception as e:
        result.error = str(e)
        logger.exception("Unexpected error in email poll")

    with _result_lock:
        _last_result = result

    logger.info(
        "Email poll complete: scanned=%d queued=%d error=%r",
        result.emails_scanned, result.attachments_queued, result.error or None,
    )
    return result


def _process_message(msg: email.message.Message) -> int:
    """
    Walk one email message, download supported attachments, queue ingest jobs.
    Returns the number of files queued.
    """
    from src.ingest_tracker import tracker

    # Import here to avoid circular import at module load time
    from src.ui.flask_app import _process_file_job

    queued = 0
    settings.docs_dir.mkdir(parents=True, exist_ok=True)

    for part in msg.walk():
        # Skip multipart containers and inline content (no Content-Disposition)
        if part.get_content_maintype() == "multipart":
            continue
        disposition = part.get("Content-Disposition", "")
        if not disposition:
            continue

        filename = part.get_filename()
        if not filename:
            continue

        filename = _decode_header_str(filename)
        suffix = Path(filename).suffix.lower()

        if suffix not in ALLOWED_EXTENSIONS:
            logger.debug("Skipping unsupported attachment type: %s", filename)
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            logger.debug("Empty payload for %s, skipping", filename)
            continue

        # Avoid overwriting an existing file — append _email suffix
        dest = settings.docs_dir / filename
        if dest.exists():
            stem = Path(filename).stem
            dest = settings.docs_dir / f"{stem}_email{suffix}"

        dest.write_bytes(payload)
        logger.info("Saved email attachment → %s (%d bytes)", dest.name, len(payload))

        job_id = tracker.enqueue(dest.name)
        t = threading.Thread(
            target=_process_file_job,
            args=(job_id, dest, dest.name),
            kwargs={"high_quality": False},
            daemon=True,
        )
        t.start()
        queued += 1

    return queued


def _decode_header_str(value: str) -> str:
    """Decode RFC 2047-encoded email header strings (handles non-ASCII filenames/subjects)."""
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for chunk, charset in parts:
        if isinstance(chunk, bytes):
            decoded.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(str(chunk))
    return "".join(decoded).strip()
