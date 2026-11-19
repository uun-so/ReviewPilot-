"""HTTP request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_ARTICLE_CHARS = 200_000


class CheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article_text: str = Field(min_length=1, max_length=MAX_ARTICLE_CHARS)
    article_name: str = Field(default="article.md", max_length=200)
    kb: str = Field(min_length=1, max_length=64)
    allow_confidential: bool = False


class KbOut(BaseModel):
    id: str
    name: str
    version: str
    sensitivity: str
    indexed: bool
    documents: int | None = None
    chunks: int | None = None
    error: str | None = None


class KbIndexOut(BaseModel):
    id: str
    name: str
    version: str
    sensitivity: str
    documents: int
    chunks: int


class JobOut(BaseModel):
    id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    article_name: str
    kb: str
    summary: dict[str, int] | None = None
    error: str | None = None
    result_url: str | None = None
    report_url: str | None = None


class HealthOut(BaseModel):
    status: str = "ok"
    version: str
    api_key_configured: bool
    kb_root: str
    runs_dir: str
    concurrency: int
    models: dict[str, str]
    max_article_chars: int = MAX_ARTICLE_CHARS
