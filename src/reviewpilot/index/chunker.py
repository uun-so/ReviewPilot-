"""Structure-aware chunking with block-boundary overlap.

A chunk is a retrieval unit, not an evidence unit. Evidence quotes are always
validated against the full document text, so overlapping text in neighbouring
chunks cannot create a false citation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from reviewpilot.ingest.blocks import Block, Document

_CJK = re.compile(r"[一-鿿]")
_ASCII_WORD = re.compile(r"[A-Za-z0-9_]+")
_SENTENCE = re.compile(r"[^。！？!?\n]+[。！？!?]?|\n+")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    ord: int
    text: str
    heading_path: str
    char_start: int
    char_end: int
    token_count: int


def estimate_tokens(text: str) -> int:
    """Cheap token estimate: CJK characters + ASCII word runs."""
    return len(_CJK.findall(text)) + len(_ASCII_WORD.findall(text))


def _slice_block(block: Block, start: int, end: int) -> Block:
    return Block(
        kind=block.kind,
        text=block.text[start:end],
        char_start=block.char_start + start,
        char_end=block.char_start + end,
        heading_path=block.heading_path,
    )


def split_block(block: Block, max_tokens: int) -> list[Block]:
    """Split an oversized block at sentence boundaries, then by characters."""
    if estimate_tokens(block.text) <= max_tokens:
        return [block]

    pieces: list[Block] = []
    buffer_start: int | None = None
    buffer_end = 0

    for match in _SENTENCE.finditer(block.text):
        segment = match.group(0)
        if not segment:
            continue

        if estimate_tokens(segment) > max_tokens:
            if buffer_start is not None:
                pieces.append(_slice_block(block, buffer_start, buffer_end))
                buffer_start = None
            ratio = max_tokens / max(1, estimate_tokens(segment))
            step = max(1, int(len(segment) * ratio))
            for offset in range(0, len(segment), step):
                pieces.append(
                    _slice_block(
                        block,
                        match.start() + offset,
                        min(match.start() + offset + step, match.end()),
                    )
                )
            continue

        if (
            buffer_start is not None
            and estimate_tokens(block.text[buffer_start : match.end()]) > max_tokens
        ):
            pieces.append(_slice_block(block, buffer_start, buffer_end))
            buffer_start = None

        if buffer_start is None:
            buffer_start = match.start()
        buffer_end = match.end()

    if buffer_start is not None:
        pieces.append(_slice_block(block, buffer_start, buffer_end))

    return [piece for piece in pieces if piece.text.strip()]


def chunk_document(
    doc: Document, *, target_tokens: int = 500, max_tokens: int = 600
) -> list[Chunk]:
    prepared: list[Block] = []
    for block in doc.blocks:
        if block.text.strip():
            prepared.extend(split_block(block, max_tokens))

    groups: list[list[Block]] = []
    current: list[Block] = []
    current_tokens = 0

    def flush() -> None:
        if current:
            groups.append(list(current))

    for block in prepared:
        block_tokens = estimate_tokens(block.text)
        if current and current_tokens + block_tokens > max_tokens:
            flush()
            tail = current[-1]
            tail_tokens = estimate_tokens(tail.text)
            if (
                tail.kind != "heading"
                and tail_tokens <= max(1, int(target_tokens * 0.25))
                and tail_tokens + block_tokens <= max_tokens
            ):
                current = [tail]
                current_tokens = tail_tokens
            else:
                current = []
                current_tokens = 0
        current.append(block)
        current_tokens += block_tokens

    flush()

    chunks: list[Chunk] = []
    for group in groups:
        text = "\n".join(block.text for block in group)
        if not text.strip():
            continue
        ordinal = len(chunks) + 1
        heading_path = " > ".join(group[-1].heading_path)
        chunks.append(
            Chunk(
                chunk_id=f"{doc.doc_id}#c{ordinal:04d}",
                doc_id=doc.doc_id,
                ord=ordinal,
                text=text,
                heading_path=heading_path,
                char_start=min(block.char_start for block in group),
                char_end=max(block.char_end for block in group),
                token_count=estimate_tokens(text),
            )
        )
    return chunks
