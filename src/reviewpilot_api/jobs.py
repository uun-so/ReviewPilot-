"""In-process job queue for article checks.

A single worker thread runs one check at a time. Each check already uses the
configured model concurrency internally, so multiple concurrent jobs would
multiply API concurrency and hit provider limits. Jobs are intentionally
in-memory; completed artifacts remain on disk under ``runs/``.
"""

from __future__ import annotations

import copy
import logging
import queue
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from reviewpilot.config import AppConfig
from reviewpilot.llm.provider import DeepSeekProvider, LLMProvider
from reviewpilot.pipeline import CheckOptions, run_check
from reviewpilot_api.registry import KbRegistry

logger = logging.getLogger(__name__)

ProviderFactory = Callable[[], LLMProvider]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Job:
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
    article_name: str
    kb_id: str
    allow_confidential: bool
    input_path: Path
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    run_id: str | None = None
    run_dir: Path | None = None
    summary: dict[str, int] | None = None


def _snapshot(job: Job) -> Job:
    return copy.deepcopy(job)


class JobManager:
    def __init__(
        self,
        runs_dir: Path,
        config: AppConfig,
        registry: KbRegistry,
        provider_factory: ProviderFactory | None = None,
    ) -> None:
        self.runs_dir = runs_dir.resolve()
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.registry = registry
        self.provider_factory: ProviderFactory = provider_factory or DeepSeekProvider
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._worker, name="reviewpilot-worker", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=10)

    def submit(
        self,
        *,
        article_text: str,
        article_name: str,
        kb_id: str,
        allow_confidential: bool,
    ) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job_dir = self.runs_dir / "_jobs" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(article_name).suffix.lower()
        if suffix not in {".md", ".markdown", ".txt"}:
            suffix = ".md"
        input_path = job_dir / f"input{suffix}"
        input_path.write_text(article_text, encoding="utf-8")

        now = _utcnow()
        job = Job(
            id=job_id,
            status="queued",
            created_at=now,
            updated_at=now,
            article_name=article_name,
            kb_id=kb_id,
            allow_confidential=allow_confidential,
            input_path=input_path,
        )
        with self._lock:
            self._jobs[job_id] = job
        self._queue.put(job_id)
        return _snapshot(job)

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return _snapshot(job) if job is not None else None

    def list(self, *, limit: int = 20) -> list[Job]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.created_at, reverse=True)
            return [_snapshot(job) for job in jobs[:limit]]

    def _update(self, job_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in fields.items():
                setattr(job, key, value)
            job.updated_at = _utcnow()

    def _worker(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                if job_id is None:
                    return
                self._run(job_id)
            finally:
                self._queue.task_done()

    def _run(self, job_id: str) -> None:
        job = self.get(job_id)
        if job is None:
            return
        self._update(job_id, status="running", started_at=_utcnow())
        try:
            provider = self.provider_factory()
            kb_dir = self.registry.resolve(job.kb_id)
            result, run_dir = run_check(
                CheckOptions(
                    article_path=job.input_path,
                    kb_dir=kb_dir,
                    out_dir=self.runs_dir,
                    config=self.config,
                    provider=provider,
                    store_article=True,
                    concurrency=self.config.concurrency,
                )
            )
            self._update(
                job_id,
                status="succeeded",
                finished_at=_utcnow(),
                run_id=result.run.run_id,
                run_dir=run_dir,
                summary=result.summary.model_dump(),
            )
        except Exception as exc:  # job failures are data, not process crashes
            logger.exception("job %s failed", job_id)
            self._update(
                job_id,
                status="failed",
                finished_at=_utcnow(),
                error=str(exc),
            )
