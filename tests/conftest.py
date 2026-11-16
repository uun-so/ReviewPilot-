from pathlib import Path

import pytest


@pytest.fixture
def kb_dir(tmp_path: Path) -> Path:
    (tmp_path / "sources").mkdir()
    markdown = (
        "# HTTP\n\n"
        "HTTPConnection timeout 是超时时间；默认值为 30 秒。\n\n"
        "```python\n"
        "conn = HTTPConnection()\n"
        "```\n\n"
        "| 参数 | 默认值 |\n"
        "|---|---|\n"
        "| timeout | 30 |\n"
    )
    (tmp_path / "sources" / "http.md").write_text(markdown, encoding="utf-8")

    html = (
        "<html><head><title>JSON</title></head><body>"
        "<h1>JSON</h1>"
        "<p>json.dumps 的 ensure_ascii 默认为 True。</p>"
        "<ul><li>indent 控制缩进。</li></ul>"
        "</body></html>"
    )
    (tmp_path / "sources" / "json.html").write_text(html, encoding="utf-8")

    manifest = (
        'name: test-kb\n'
        'version: "1.0"\n'
        'effective_date: 2026-11-14\n'
        'sensitivity: public\n'
        'sources:\n'
        '  - path: sources/http.md\n'
        '    title: HTTP\n'
        '    format: markdown\n'
        '    version: "3.13"\n'
        '  - path: sources/json.html\n'
        '    title: JSON\n'
        '    format: html\n'
        '    version: "3.13"\n'
    )
    (tmp_path / "manifest.yaml").write_text(manifest, encoding="utf-8")
    return tmp_path
