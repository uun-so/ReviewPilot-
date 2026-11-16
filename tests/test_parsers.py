from pathlib import Path

from reviewpilot.ingest.html import parse_html
from reviewpilot.ingest.markdown import parse_markdown
from reviewpilot.ingest.text import parse_text


def test_markdown_offsets_and_kinds() -> None:
    raw = (
        "# Title\n\n"
        "第一段。\n\n"
        "```python\nprint('x')\n```\n\n"
        "| 参数 | 默认值 |\n|---|---|\n| timeout | 30 |\n"
    )
    blocks = parse_markdown(raw)
    assert {block.kind for block in blocks} >= {"heading", "paragraph", "code", "table"}
    for block in blocks:
        assert raw[block.char_start : block.char_end] == block.text
    assert blocks[0].text == "Title"
    assert blocks[0].heading_path == ("Title",)
    assert blocks[1].heading_path == ("Title",)


def test_html_offsets_and_title() -> None:
    raw = (
        "<html><head><title>Demo</title></head><body>"
        "<h1>Heading</h1><p>第一段。</p><ul><li>列表项。</li></ul>"
        "</body></html>"
    )
    normalized, blocks, title = parse_html(raw)
    assert title == "Demo"
    assert normalized
    for block in blocks:
        assert normalized[block.char_start : block.char_end] == block.text
    assert any(block.kind == "heading" and block.text == "Heading" for block in blocks)
    assert any(block.kind == "list" and "列表项" in block.text for block in blocks)


def test_plain_text_offsets() -> None:
    raw = "第一段。\n\n第二段。\n"
    blocks = parse_text(raw)
    assert len(blocks) == 2
    for block in blocks:
        assert raw[block.char_start : block.char_end] == block.text
