"""Plain-text paragraph parser preserving character offsets."""

from __future__ import annotations

from reviewpilot.ingest.blocks import Block


def parse_text(raw: str) -> list[Block]:
    lines = raw.splitlines(keepends=True)
    starts: list[int] = []
    position = 0
    for line in lines:
        starts.append(position)
        position += len(line)
    starts.append(position)

    blocks: list[Block] = []
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        j = i + 1
        while j < len(lines) and lines[j].strip():
            j += 1
        start, end = starts[i], starts[j]
        blocks.append(Block("paragraph", raw[start:end], start, end, ()))
        i = j
    return blocks
