"""Line-based Markdown block parser that preserves character offsets.

We intentionally do not render Markdown to HTML: rendering loses the byte
positions needed to validate exact evidence quotes. Headings, paragraphs,
lists, tables and fenced code blocks are recognized; inline Markdown remains
part of the block text and therefore part of the normalized source.
"""

from __future__ import annotations

import re

from reviewpilot.ingest.blocks import Block

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


def _line_starts(raw: str) -> tuple[list[str], list[int]]:
    lines = raw.splitlines(keepends=True)
    starts: list[int] = []
    position = 0
    for line in lines:
        starts.append(position)
        position += len(line)
    starts.append(position)
    return lines, starts


def parse_markdown(raw: str) -> list[Block]:
    lines, starts = _line_starts(raw)
    blocks: list[Block] = []
    heading_stack: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        fence = _FENCE.match(line)
        if fence:
            marker = fence.group(1)
            j = i + 1
            while j < len(lines):
                if re.match(rf"^\s*{re.escape(marker)}", lines[j]):
                    j += 1
                    break
                j += 1
            start, end = starts[i], starts[j]
            blocks.append(
                Block("code", raw[start:end], start, end, tuple(heading_stack))
            )
            i = j
            continue

        heading = _HEADING.match(line.rstrip("\r\n"))
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            title_start = starts[i] + heading.start(2)
            title_end = starts[i] + heading.end(2)
            heading_stack = heading_stack[: level - 1] + [title]
            blocks.append(
                Block(
                    "heading",
                    raw[title_start:title_end],
                    title_start,
                    title_end,
                    tuple(heading_stack),
                )
            )
            i += 1
            continue

        if (
            "|" in line
            and i + 1 < len(lines)
            and "-" in lines[i + 1]
            and _TABLE_SEPARATOR.match(lines[i + 1])
        ):
            j = i + 2
            while j < len(lines) and lines[j].strip() and "|" in lines[j]:
                j += 1
            start, end = starts[i], starts[j]
            blocks.append(
                Block("table", raw[start:end], start, end, tuple(heading_stack))
            )
            i = j
            continue

        if _LIST_ITEM.match(line):
            j = i + 1
            while j < len(lines):
                if not lines[j].strip():
                    break
                if _LIST_ITEM.match(lines[j]) or lines[j].startswith((" ", "\t")):
                    j += 1
                    continue
                break
            start, end = starts[i], starts[j]
            blocks.append(
                Block("list", raw[start:end], start, end, tuple(heading_stack))
            )
            i = j
            continue

        j = i + 1
        while j < len(lines):
            candidate = lines[j]
            if not candidate.strip():
                break
            if _FENCE.match(candidate) or _HEADING.match(candidate.rstrip("\r\n")):
                break
            if _LIST_ITEM.match(candidate):
                break
            if (
                "|" in candidate
                and j + 1 < len(lines)
                and "-" in lines[j + 1]
                and _TABLE_SEPARATOR.match(lines[j + 1])
            ):
                break
            j += 1
        start, end = starts[i], starts[j]
        blocks.append(
            Block("paragraph", raw[start:end], start, end, tuple(heading_stack))
        )
        i = j

    return blocks
