"""SQLite FTS5 index build, inspection, and BM25 search.

Chinese text is segmented with jieba before insertion because FTS5's built-in
tokenizers treat a whole CJK run as one token (and trigram cannot match
two-character queries). Tokens are stored space-separated; original chunk text
is kept for display and evidence anchoring.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import jieba

from reviewpilot.index.chunker import Chunk, chunk_document, estimate_tokens
from reviewpilot.ingest.loader import load_document
from reviewpilot.ingest.manifest import load_manifest

jieba.setLogLevel(logging.ERROR)

_CJK_RUN = re.compile(r"[一-鿿]+")
_ASCII_TOKEN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.:/#\-]*")

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_version TEXT,
    format TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    text TEXT NOT NULL
);
CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(doc_id),
    ord INTEGER NOT NULL,
    heading_path TEXT NOT NULL,
    text TEXT NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    token_count INTEGER NOT NULL
);
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    chunk_id UNINDEXED,
    tokens,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""


@dataclass(frozen=True)
class IndexStats:
    index_path: Path
    documents: int
    chunks: int
    manifest_name: str
    manifest_version: str
    manifest_sha256: str
    sensitivity: str


@dataclass(frozen=True)
class IndexInspection:
    index_path: Path
    meta: dict[str, str]
    documents: int
    chunks: int


_EN_STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "of",
    "to",
    "in",
    "on",
    "and",
    "or",
    "for",
    "with",
    "as",
    "by",
    "this",
    "that",
    "it",
    "be",
    "at",
    "from",
}


def tokenize(text: str) -> list[str]:
    """Tokenize mixed Chinese/English text for indexing and querying."""
    tokens: list[str] = []
    for run in _CJK_RUN.findall(text):
        tokens.extend(token for token in jieba.cut_for_search(run) if token.strip())
    tokens.extend(token.lower() for token in _ASCII_TOKEN.findall(text))
    return tokens


def query_tokens(text: str) -> list[str]:
    """Query-side filtering: drop Chinese single characters and EN stopwords.

    If filtering removes everything, fall back to the raw tokens so a query
    made only of stopwords still returns something the judge can reject.
    """
    raw = list(dict.fromkeys(tokenize(text)))
    filtered = [
        token
        for token in raw
        if (token.isascii() and token not in _EN_STOPWORDS)
        or (not token.isascii() and len(token) > 1)
    ]
    return filtered or raw


def _quoted(token: str) -> str:
    return '"' + token.replace('"', '""') + '"'


def _and_expression(tokens: list[str]) -> str:
    return " AND ".join(_quoted(token) for token in tokens)


def _or_expression(tokens: list[str]) -> str:
    return " OR ".join(_quoted(token) for token in tokens)


def _match_expression(query: str) -> str:
    """Legacy helper retained for debugging; search tries AND then OR."""
    tokens = query_tokens(query)
    if not tokens:
        return ""
    return _or_expression(tokens)


def build_index(kb_dir: Path) -> IndexStats:
    kb_dir = kb_dir.resolve()
    loaded = load_manifest(kb_dir)
    documents = [load_document(source) for source in loaded.sources]

    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(chunk_document(document))

    index_path = kb_dir / "index.sqlite"
    temp_path = kb_dir / "index.sqlite.tmp"
    if temp_path.exists():
        temp_path.unlink()

    connection = sqlite3.connect(temp_path)
    try:
        connection.executescript(SCHEMA)
        for document in documents:
            connection.execute(
                """
                INSERT INTO documents
                    (doc_id, title, source_path, source_version, format, sha256, char_count, text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document.doc_id,
                    document.title,
                    document.source_path,
                    document.source_version,
                    document.format,
                    document.sha256,
                    len(document.text),
                    document.text,
                ),
            )
        for chunk in chunks:
            connection.execute(
                """
                INSERT INTO chunks
                    (chunk_id, doc_id, ord, heading_path, text, char_start, char_end, token_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.chunk_id,
                    chunk.doc_id,
                    chunk.ord,
                    chunk.heading_path,
                    chunk.text,
                    chunk.char_start,
                    chunk.char_end,
                    chunk.token_count,
                ),
            )
            connection.execute(
                "INSERT INTO chunks_fts (chunk_id, tokens) VALUES (?, ?)",
                (chunk.chunk_id, " ".join(tokenize(chunk.text))),
            )

        meta = {
            "schema_version": "1",
            "manifest_name": loaded.manifest.name,
            "manifest_version": loaded.manifest.version,
            "manifest_effective_date": loaded.manifest.effective_date.isoformat(),
            "manifest_sha256": loaded.manifest_sha256,
            "sensitivity": loaded.manifest.sensitivity,
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_count": str(len(documents)),
            "chunk_count": str(len(chunks)),
            "tokenizer": "jieba+unicode61",
        }
        connection.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)", meta.items()
        )
        connection.commit()
    except Exception:
        connection.close()
        if temp_path.exists():
            temp_path.unlink()
        raise
    else:
        connection.close()

    os.replace(temp_path, index_path)
    return IndexStats(
        index_path=index_path,
        documents=len(documents),
        chunks=len(chunks),
        manifest_name=loaded.manifest.name,
        manifest_version=loaded.manifest.version,
        manifest_sha256=loaded.manifest_sha256,
        sensitivity=loaded.manifest.sensitivity,
    )


def inspect_index(kb_dir: Path) -> IndexInspection:
    index_path = (kb_dir / "index.sqlite").resolve()
    if not index_path.exists():
        raise FileNotFoundError(f"索引不存在：{index_path}（先运行 kb index）")
    connection = sqlite3.connect(index_path)
    try:
        meta = dict(connection.execute("SELECT key, value FROM meta").fetchall())
        documents = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chunks = connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    finally:
        connection.close()
    return IndexInspection(
        index_path=index_path, meta=meta, documents=documents, chunks=chunks
    )


def search_index(kb_dir: Path, query: str, *, limit: int = 6) -> list[dict]:
    """Return BM25-ranked chunks.

    Multi-token queries try AND first (precision), then OR (recall). A result
    that only matches one weak token is still returned in OR mode; the
    evidence gate, not retrieval, decides support. ``score`` is lower-is-better
    (FTS5 bm25).
    """
    index_path = (kb_dir / "index.sqlite").resolve()
    if not index_path.exists():
        raise FileNotFoundError(f"索引不存在：{index_path}（先运行 kb index）")
    tokens = query_tokens(query)
    if not tokens:
        return []

    connection = sqlite3.connect(index_path)
    connection.row_factory = sqlite3.Row
    try:
        def run(expression: str, mode: str) -> list[dict]:
            rows = connection.execute(
                """
                SELECT
                    c.chunk_id, c.doc_id, c.ord, c.heading_path, c.text,
                    c.char_start, c.char_end, c.token_count,
                    d.title, d.source_path, d.source_version, d.format,
                    d.text AS document_text,
                    bm25(chunks_fts) AS score
                FROM chunks_fts
                JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
                JOIN documents d ON d.doc_id = c.doc_id
                WHERE chunks_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (expression, limit),
            ).fetchall()
            results = [dict(row) for row in rows]
            for result in results:
                result["match_mode"] = mode
            return results

        if len(tokens) > 1:
            results = run(_and_expression(tokens), "and")
            if results:
                return results
        return run(_or_expression(tokens), "or")
    finally:
        connection.close()
