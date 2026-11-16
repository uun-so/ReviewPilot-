"""Dispatch a loaded source to the right parser and build a Document."""

from __future__ import annotations

from reviewpilot.ingest.blocks import Block, Document
from reviewpilot.ingest.html import parse_html
from reviewpilot.ingest.manifest import LoadedSource
from reviewpilot.ingest.markdown import parse_markdown
from reviewpilot.ingest.text import parse_text


def load_document(source: LoadedSource) -> Document:
    fmt = source.spec.format
    if fmt == "markdown":
        text = source.text
        blocks: list[Block] = parse_markdown(source.text)
        title = source.spec.title
    elif fmt == "html":
        text, blocks, html_title = parse_html(source.text)
        title = source.spec.title or html_title or source.spec.path
    else:
        text = source.text
        blocks = parse_text(source.text)
        title = source.spec.title

    if not blocks:
        raise ValueError(f"{source.spec.path}: 未解析到任何文本块")

    return Document(
        doc_id=source.spec.path,
        title=title,
        source_path=source.spec.path,
        source_version=source.spec.version,
        format=fmt,
        sha256=source.sha256,
        text=text,
        blocks=tuple(blocks),
    )
