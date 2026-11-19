"""Knowledge-base discovery for the HTTP API.

Only immediate subdirectories of the configured KB root that contain a
manifest are exposed. The directory name is the public KB id; paths never come
from the request, so traversal is impossible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from reviewpilot.index.fts import IndexStats, build_index, inspect_index
from reviewpilot.ingest.manifest import load_manifest

_KB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class KbNotFound(KeyError):
    """Raised when a requested KB id is not a configured KB."""


@dataclass(frozen=True)
class KbInfo:
    id: str
    name: str
    version: str
    sensitivity: str
    indexed: bool
    documents: int | None = None
    chunks: int | None = None
    error: str | None = None


class KbRegistry:
    def __init__(self, kb_root: Path):
        self.kb_root = kb_root.resolve()

    def _candidate_dirs(self) -> list[Path]:
        if not self.kb_root.is_dir():
            return []
        return sorted(
            path
            for path in self.kb_root.iterdir()
            if path.is_dir()
            and (
                (path / "manifest.yaml").is_file()
                or (path / "manifest.yml").is_file()
            )
        )

    def list(self) -> list[KbInfo]:
        return [self._info(path) for path in self._candidate_dirs()]

    def resolve(self, kb_id: str) -> Path:
        if not _KB_ID.fullmatch(kb_id):
            raise KbNotFound(kb_id)
        path = (self.kb_root / kb_id).resolve()
        if not path.is_dir() or not path.is_relative_to(self.kb_root):
            raise KbNotFound(kb_id)
        if not (path / "manifest.yaml").is_file() and not (path / "manifest.yml").is_file():
            raise KbNotFound(kb_id)
        return path

    def info(self, kb_id: str) -> KbInfo:
        return self._info(self.resolve(kb_id))

    def _info(self, path: Path) -> KbInfo:
        try:
            loaded = load_manifest(path)
        except Exception as exc:  # manifest problems are reported per KB, not fatal
            return KbInfo(
                id=path.name,
                name=path.name,
                version="?",
                sensitivity="?",
                indexed=False,
                error=str(exc),
            )

        indexed = (path / "index.sqlite").is_file()
        documents = chunks = None
        error = None
        if indexed:
            try:
                inspection = inspect_index(path)
                documents = inspection.documents
                chunks = inspection.chunks
            except Exception as exc:
                error = f"索引读取失败：{exc}"

        return KbInfo(
            id=path.name,
            name=loaded.manifest.name,
            version=loaded.manifest.version,
            sensitivity=loaded.manifest.sensitivity,
            indexed=indexed,
            documents=documents,
            chunks=chunks,
            error=error,
        )

    def index(self, kb_id: str) -> IndexStats:
        return build_index(self.resolve(kb_id))
