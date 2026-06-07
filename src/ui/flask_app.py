"""
STEWARD — Flask UI
Routes: / · /ingest · /documents · /about
"""
from __future__ import annotations

import logging
import os
import sqlite3
import subprocess
import tempfile
import threading
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from src.config import settings
from src.database import init_db
from src.email_ingest import get_last_result as get_email_status
from src.ingest_tracker import tracker
from src.scheduler import start_scheduler, stop_scheduler, trigger_email_poll_now

logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)
app.secret_key = "steward-local-only"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}

# Limit concurrent Claude API calls — scanned PDFs with many pages send large payloads.
# More than 2 simultaneous calls reliably causes timeouts.
_api_semaphore = threading.Semaphore(2)


def _boot_error() -> str | None:
    if not settings.has_api_key:
        return "No Anthropic API key found. Set ANTHROPIC_API_KEY in your .env file."
    return None


@app.context_processor
def inject_globals():
    from src.database import count_documents
    email_status = get_email_status()
    return {
        "doc_count":        count_documents(),
        "boot_error":       _boot_error(),
        "active_uploads":   tracker.count_active(),
        "email_configured": bool(settings.steward_email and settings.steward_email_password),
        "steward_email":    settings.steward_email or "",
        "email_status":     email_status,
    }


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    from src.database import get_documents_due_within_days
    upcoming = get_documents_due_within_days(30)
    return render_template("index.html", upcoming=upcoming)


# ── Ingest ────────────────────────────────────────────────────────────────────

@app.route("/ingest", methods=["GET", "POST"])
def ingest():
    if request.method == "POST":
        error = _boot_error()
        if error:
            flash(error, "error")
            return redirect(url_for("index"))

        # ── Text paste: keep synchronous (fast) ──────────────────────────
        paste_text = request.form.get("paste_text", "").strip()
        paste_title = request.form.get("paste_title", "pasted-text").strip()
        if paste_text:
            return _ingest_text(paste_text, paste_title)

        # ── File upload: save to disk immediately, process in background ──
        files = request.files.getlist("files")
        if not files or files[0].filename == "":
            flash("No file selected and no text pasted.", "warning")
            return redirect(url_for("ingest"))

        settings.docs_dir.mkdir(parents=True, exist_ok=True)
        job_ids: list[str] = []

        for f in files:
            filename = f.filename
            suffix = Path(filename).suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                flash(f"{filename}: unsupported type ({suffix}). Use PDF, DOCX, TXT.", "error")
                continue

            dest = settings.docs_dir / filename
            f.save(str(dest))                    # save immediately so request can end
            job_id = tracker.enqueue(filename)   # register job
            job_ids.append(job_id)

            t = threading.Thread(
                target=_process_file_job,
                args=(job_id, dest, filename),
                daemon=True,
            )
            t.start()

        # Store job IDs in session so progress survives tab navigation
        session["recent_jobs"] = list(dict.fromkeys(
            job_ids + session.get("recent_jobs", [])
        ))[:30]   # keep last 30

        return redirect(url_for("ingest"))

    # ── GET: pull recent jobs from session ────────────────────────────────
    tracker.purge_old()
    recent_jobs = tracker.get_jobs(session.get("recent_jobs", []))
    return render_template("ingest.html", recent_jobs=recent_jobs, settings=settings)


@app.route("/ingest/status")
def ingest_status():
    """JSON endpoint: returns current status of requested job IDs."""
    ids = [i for i in request.args.get("ids", "").split(",") if i]
    jobs = tracker.get_jobs(ids)
    return jsonify({"jobs": jobs, "active": tracker.count_active()})


def _process_file_job(job_id: str, dest: Path, filename: str, high_quality: bool = False) -> None:
    """Background thread: parse, extract, and store one file. Updates tracker throughout.

    Args:
        high_quality: If True, render scanned pages at 150 DPI (vs default 100 DPI) and
                      use Sonnet for vision extraction. Set for re-ingests where the first
                      pass produced bad results on a scanned/image document.
    """
    from src.database import document_exists, insert_document
    from src.doc_parser import compute_sha256, parse_document
    from src.extractor import extract

    image_dpi = 150 if high_quality else 100

    try:
        tracker.set_processing(job_id)

        sha256 = compute_sha256(dest)
        if document_exists(sha256):
            tracker.set_duplicate(job_id)
            return

        # Keep tmp_dir alive until AFTER extract() — it holds the PNG images
        # for scanned PDFs that Claude needs to read.
        import shutil
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            parsed = parse_document(dest, tmp_dir=tmp_dir, image_dpi=image_dpi)

            if not parsed.success:
                tracker.set_error(job_id, f"Parse error: {parsed.error}")
                return

            file_size_bytes = dest.stat().st_size
            with _api_semaphore:   # max 2 concurrent Claude calls
                result = extract(parsed, doc_path=str(dest), file_size_bytes=file_size_bytes)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        if not result.success:
            tracker.set_error(job_id, f"Extraction error: {result.error}")
            return

        try:
            insert_document(result.card)
        except sqlite3.IntegrityError:
            tracker.set_duplicate(job_id)
            return

        tracker.set_done(job_id, result.card.item or filename)

    except Exception as exc:
        logger.exception("Unexpected error processing %s", filename)
        tracker.set_error(job_id, str(exc))


def _ingest_text(text: str, title: str):
    """Ingest pasted plain text."""
    from src.database import document_exists, insert_document
    from src.doc_parser import parse_text_content
    from src.extractor import extract

    parsed = parse_text_content(text, title)

    if document_exists(parsed.sha256):
        flash("This text has already been ingested (duplicate detected).", "warning")
        return redirect(url_for("ingest"))

    result = extract(parsed, doc_path="pasted-text")

    if not result.success:
        flash(f"Extraction error: {result.error}", "error")
        return redirect(url_for("ingest"))

    insert_document(result.card)
    flash(f"✓ Saved as '{result.card.item or title}'", "success")
    return redirect(url_for("documents"))


# ── Documents ─────────────────────────────────────────────────────────────────

@app.route("/documents")
def documents():
    from src.database import get_all_documents
    from datetime import date
    docs = get_all_documents()
    today = date.today().isoformat()
    return render_template("documents.html", docs=docs, today=today)


@app.route("/documents/<int:doc_id>/open")
def open_document(doc_id):
    """Open the document file in the user's default Mac app (Preview, Word, etc.)."""
    from src.database import get_document_by_id
    doc = get_document_by_id(doc_id)
    if doc:
        path = Path(doc.doc_path)
        if path.exists():
            subprocess.Popen(["open", str(path)])
        else:
            flash(f"File not found on disk: {doc.doc_path}", "error")
    return redirect(url_for("documents"))


@app.route("/documents/<int:doc_id>/reingest", methods=["POST"])
def reingest_document(doc_id):
    """Delete the existing DB record and re-run extraction on the saved file."""
    from src.database import delete_document, get_document_by_id
    doc = get_document_by_id(doc_id)
    if not doc:
        flash("Document not found.", "error")
        return redirect(url_for("documents"))

    path = Path(doc.doc_path)
    if not path.exists():
        flash(f"File not on disk: {doc.doc_path}. Cannot re-ingest.", "error")
        return redirect(url_for("documents"))

    delete_document(doc_id)

    job_id = tracker.enqueue(doc.filename)
    session["recent_jobs"] = [job_id] + session.get("recent_jobs", [])

    t = threading.Thread(
        target=_process_file_job,
        args=(job_id, path, doc.filename),
        kwargs={"high_quality": True},   # re-ingests use 150 DPI + Sonnet vision
        daemon=True,
    )
    t.start()

    flash(f"Re-processing {doc.filename} at higher quality… check Upload page for progress.", "info")
    return redirect(url_for("ingest"))


@app.route("/documents/<int:doc_id>/done", methods=["POST"])
def toggle_done(doc_id):
    """Toggle a document's status between active and done."""
    from src.database import get_document_by_id, update_document_status
    doc = get_document_by_id(doc_id)
    if doc:
        new_status = "active" if doc.status == "done" else "done"
        update_document_status(doc_id, new_status)
    return redirect(url_for("documents"))


# ── Ask ───────────────────────────────────────────────────────────────────────

@app.route("/ask", methods=["GET", "POST"])
def ask():
    history = session.get("chat_history", [])   # [{role, content}, ...]

    if request.method == "POST":
        action = request.form.get("action", "ask")

        if action == "clear":
            session.pop("chat_history", None)
            return redirect(url_for("ask"))

        error = _boot_error()
        if error:
            flash(error, "error")
            return redirect(url_for("index"))

        question = request.form.get("question", "").strip()
        if question:
            from src.query_engine import answer_question
            result = answer_question(question, history=history)
            if result.error:
                flash(f"Error: {result.error}", "error")
            else:
                history = history + [
                    {"role": "user",      "content": question},
                    {"role": "assistant", "content": result.text},
                ]
                session["chat_history"] = history[-40:]  # keep last 20 exchanges

    from src.database import get_all_documents
    docs = get_all_documents()
    return render_template("ask.html", history=session.get("chat_history", []), docs=docs)


# ── Email ─────────────────────────────────────────────────────────────────────

@app.route("/email/poll", methods=["POST"])
def email_poll_now():
    """Manually trigger an immediate inbox check."""
    from src.email_ingest import poll_inbox
    import threading
    # Run in background so the redirect is instant
    threading.Thread(target=poll_inbox, daemon=True).start()
    flash("Checking inbox now… refresh in a moment to see new documents.", "info")
    return redirect(url_for("ingest"))


@app.route("/email/status")
def email_status_json():
    """JSON status for the email poller (used by the UI to update last-checked time)."""
    status = get_email_status()
    if status:
        return jsonify({
            "configured": True,
            "success": status.success,
            "checked_at": status.checked_at.isoformat(),
            "emails_scanned": status.emails_scanned,
            "attachments_queued": status.attachments_queued,
            "error": status.error,
        })
    return jsonify({"configured": bool(settings.steward_email), "checked_at": None})


# ── About ─────────────────────────────────────────────────────────────────────

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/architecture")
def architecture():
    return render_template("architecture.html")


@app.route("/health")
def health():
    """HELM health endpoint — returns JSON status for the control plane."""
    from src.database import get_db
    try:
        conn = get_db()
        doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        active_count = conn.execute("SELECT COUNT(*) FROM documents WHERE status='active'").fetchone()[0]
        conn.close()
        db_ok = True
    except Exception:
        doc_count = active_count = 0
        db_ok = False

    pending_jobs = len([j for j in tracker.get_all_statuses().values()
                        if j.get("status") in ("queued", "processing")])

    return jsonify({
        "status": "running",
        "service": "steward",
        "version": "0.1.0",
        "db": "ok" if db_ok else "error",
        "documents": doc_count,
        "active_documents": active_count,
        "pending_jobs": pending_jobs,
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    settings.configure_logging()
    init_db()
    start_scheduler()
    import atexit
    atexit.register(stop_scheduler)
    port = int(os.environ.get("PORT", 5001))
    app.run(host="127.0.0.1", port=port, debug=True, use_reloader=False)
