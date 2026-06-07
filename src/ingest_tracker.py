"""
STEWARD — Background ingestion job tracker.

Thread-safe in-memory store of upload jobs so the UI can poll progress
even after the user navigates away from the Upload page.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class IngestJob:
    job_id: str
    filename: str
    status: str          # queued | processing | done | error | duplicate
    message: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "job_id":      self.job_id,
            "filename":    self.filename,
            "status":      self.status,
            "message":     self.message,
            "started_at":  self.started_at,
            "finished_at": self.finished_at,
        }


class IngestTracker:
    """Singleton that tracks all in-flight and recently completed ingest jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, IngestJob] = {}
        self._lock = threading.Lock()

    # ── Write ──────────────────────────────────────────────────────────────

    def enqueue(self, filename: str) -> str:
        """Register a new job and return its ID."""
        job_id = uuid.uuid4().hex[:10]
        with self._lock:
            self._jobs[job_id] = IngestJob(job_id=job_id, filename=filename, status="queued")
        return job_id

    def set_processing(self, job_id: str) -> None:
        self._update(job_id, status="processing")

    def set_done(self, job_id: str, message: str = "") -> None:
        self._update(job_id, status="done", message=message, finished=True)

    def set_error(self, job_id: str, message: str) -> None:
        self._update(job_id, status="error", message=message, finished=True)

    def set_duplicate(self, job_id: str) -> None:
        self._update(job_id, status="duplicate", message="Already in vault", finished=True)

    def _update(self, job_id: str, *, status: str, message: str = "", finished: bool = False) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = status
                job.message = message
                if finished:
                    job.finished_at = datetime.now().isoformat()

    # ── Read ───────────────────────────────────────────────────────────────

    def get_jobs(self, job_ids: list[str]) -> list[dict]:
        with self._lock:
            return [self._jobs[jid].to_dict() for jid in job_ids if jid in self._jobs]

    def count_active(self) -> int:
        """Number of jobs that are queued or processing right now."""
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status in ("queued", "processing"))

    # ── Housekeeping ───────────────────────────────────────────────────────

    def purge_old(self) -> None:
        """Drop finished jobs older than 60 minutes."""
        cutoff = (datetime.now() - timedelta(minutes=60)).isoformat()
        with self._lock:
            stale = [
                jid for jid, j in self._jobs.items()
                if j.finished_at and j.finished_at < cutoff
            ]
            for jid in stale:
                del self._jobs[jid]


# Module-level singleton — import this everywhere
tracker = IngestTracker()
