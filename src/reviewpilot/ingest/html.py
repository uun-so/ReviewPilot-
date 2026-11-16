"""HTML to normalized text with semantic blocks and exact offsets.

Citations point at the normalized text produced here, not at raw DOM
offsets. The original HTML is preserved by the knowledge base for audit.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from reviewpilot.ingest.blocks import Block

_HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
_SELECTED = [
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "li",
    "pre",
    "table",
    "dt",
    "dd",
]
_DROP = ["script", "style", "noscript", "nav", "footer", "header"]


def _has_selected_ancestor(element) -> bool:
    for parent in element.parents:
        if getattr(parent, "name", None) in _SELECTED:
            return True
    return False


def _kind(tag: str) -> str:
    if tag in _HEADINGS:
        return "heading"
    if tag in {"li", "dt", "dd"}:
        return "list"
    if tag == "table":
        return "table"
    if tag == "pre":
        return "code"
    return "paragraph"


def parse_html(raw: str) -> tuple[str, list[Block], str]:
    """Return ``(normalized_text, blocks, title)``."""
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(_DROP):
        tag.decompose()

    heading_stack: list[str] = []
    parts: list[str] = []
    blocks: list[Block] = []
    offset = 0

    for element in soup.find_all(_SELECTED):
        if _has_selected_ancestor(element):
            continue
        tag = element.name
        separator = "\n" if tag == "pre" else " "
        text = element.get_text(separator, strip=True)
        text = re.sub(r"[ \t]+", " ", text).strip()
        if not text:
            continue

        if tag in _HEADINGS:
            level = _HEADINGS[tag]
            heading_stack = heading_stack[: level - 1] + [text]

        if parts:
            parts.append("\n")
            offset += 1
        start = offset
        parts.append(text)
        offset += len(text)
        blocks.append(
            Block(
                _kind(tag),
                text,
                start,
                offset,
                tuple(heading_stack),
            )
        )

    normalized = "".join(parts)
    title = ""
    if soup.title and soup.title.get_text(strip=True):
        title = soup.title.get_text(" ", strip=True)
    elif blocks and blocks[0].kind == "heading":
        title = blocks[0].text

    if not blocks and normalized == "":
        body = soup.get_text("\n", strip=True)
        if body:
            normalized = body
            blocks.append(Block("paragraph", body, 0, len(body), ()))

    return normalized, blocks, title
