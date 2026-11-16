"""Deterministic sentence segmentation with exact character spans.

Code blocks are excluded from claim extraction. Tables are split by rows and
separator rows are skipped. We intentionally keep Markdown inline markers in
the sentence text so quotes can be anchored byte-for-byte.
"""

from __future__ import annotations

import re

from reviewpilot.domain import Sentence
from reviewpilot.ingest.blocks import Document

_TABLE_SEPARATOR = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
_CHINESE_END = set("。！？")
_ENGLISH_END = set("!?")


def _is_english_period(text: str, index: int) -> bool:
    if text[index] != ".":
        return False
    after = text[index + 1 :]
    if not after:
        return True
    if not after[0].isspace():
        return False
    stripped = after.lstrip()
    if not stripped:
        return True
    return stripped[0].isupper()


def _split_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    i = 0
    while i < len(text):
        char = text[i]
        boundary = False
        if char in _CHINESE_END or char in _ENGLISH_END:
            boundary = True
            while i + 1 < len(text) and text[i + 1] in (_CHINESE_END | _ENGLISH_END):
                i += 1
        elif char == "." and _is_english_period(text, i):
            boundary = True
        elif char == "\n":
            boundary = True

        if boundary:
            end = i + 1
            raw = text[start:end]
            if raw.strip():
                left = len(raw) - len(raw.lstrip())
                right = len(raw.rstrip())
                spans.append((start + left, start + right))
            start = end
        i += 1

    raw = text[start:]
    if raw.strip():
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        spans.append((start + left, start + right))
    return spans


def segment_document(document: Document) -> list[Sentence]:
    sentences: list[Sentence] = []
    counter = 0

    for block in document.blocks:
        # Headings are structural, not claims or sentences; code blocks are
        # not eligible for claim extraction either.
        if block.kind in {"code", "heading"}:
            continue

        if block.kind == "table":
            lines = block.text.splitlines(keepends=True)
            offset = 0
            for line in lines:
                if line.strip() and not _TABLE_SEPARATOR.match(line):
                    for start, end in _split_spans(line):
                        counter += 1
                        sentences.append(
                            Sentence(
                                sentence_id=f"s{counter}",
                                text=line[start:end],
                                char_start=block.char_start + offset + start,
                                char_end=block.char_start + offset + end,
                                block_kind=block.kind,
                                heading_path=" > ".join(block.heading_path),
                            )
                        )
                offset += len(line)
            continue

        for start, end in _split_spans(block.text):
            counter += 1
            sentences.append(
                Sentence(
                    sentence_id=f"s{counter}",
                    text=block.text[start:end],
                    char_start=block.char_start + start,
                    char_end=block.char_start + end,
                    block_kind=block.kind,
                    heading_path=" > ".join(block.heading_path),
                )
            )

    return sentences
