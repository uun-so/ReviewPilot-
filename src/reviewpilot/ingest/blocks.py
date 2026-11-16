"""Shared document/block models.

Offsets always refer to the normalized text stored on the document. For
Markdown and plain text that is the raw file; for HTML it is the text
extracted from semantic elements (see ``html.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

BlockKind = Literal["heading", "paragraph", "list", "table", "code"]


@dataclass(frozen=True)
class Block:
    kind: BlockKind
    text: str
    char_start: int
    char_end: int
    heading_path: tuple[str, ...] = ()


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    source_path: str
    source_version: Optional[str]
    format: str
    sha256: str
    text: str
    blocks: tuple[Block, ...]
