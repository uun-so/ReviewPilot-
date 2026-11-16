from pathlib import Path

from reviewpilot.index.fts import build_index, inspect_index, search_index


def test_build_inspect_and_search(kb_dir: Path) -> None:
    stats = build_index(kb_dir)
    assert stats.documents == 2
    assert stats.chunks >= 2
    assert (kb_dir / "index.sqlite").exists()
    assert not (kb_dir / "index.sqlite.tmp").exists()

    rows = search_index(kb_dir, "默认值", limit=3)
    assert rows
    assert rows[0]["doc_id"] == "sources/http.md"
    assert rows[0]["match_mode"] in {"and", "or"}

    rows = search_index(kb_dir, "ensure_ascii", limit=3)
    assert rows
    assert rows[0]["doc_id"] == "sources/json.html"

    assert search_index(kb_dir, "不存在的词", limit=3) == []

    inspection = inspect_index(kb_dir)
    assert inspection.documents == 2
    assert inspection.chunks == stats.chunks
    assert inspection.meta["manifest_name"] == "test-kb"
    assert inspection.meta["tokenizer"] == "jieba+unicode61"


def test_missing_index_raises(kb_dir: Path) -> None:
    try:
        inspect_index(kb_dir)
    except FileNotFoundError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected FileNotFoundError")
