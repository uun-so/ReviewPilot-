from pathlib import Path

import pytest

from reviewpilot.ingest.manifest import ManifestError, load_manifest


def test_load_manifest(kb_dir: Path) -> None:
    loaded = load_manifest(kb_dir)
    assert loaded.manifest.name == "test-kb"
    assert loaded.manifest.version == "1.0"
    assert len(loaded.sources) == 2
    assert len(loaded.manifest_sha256) == 64


def test_sha256_mismatch_is_rejected(kb_dir: Path) -> None:
    manifest_path = kb_dir / "manifest.yaml"
    text = manifest_path.read_text(encoding="utf-8")
    text = text.replace(
        "    format: markdown\n",
        '    format: markdown\n    sha256: "deadbeef"\n',
        1,
    )
    manifest_path.write_text(text, encoding="utf-8")
    with pytest.raises(ManifestError, match="哈希不匹配"):
        load_manifest(kb_dir)


def test_path_escape_is_rejected(kb_dir: Path) -> None:
    outside = kb_dir.parent / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    manifest_path = kb_dir / "manifest.yaml"
    text = manifest_path.read_text(encoding="utf-8").replace(
        "path: sources/http.md", "path: ../outside.md"
    )
    manifest_path.write_text(text, encoding="utf-8")
    with pytest.raises(ManifestError, match="逃逸"):
        load_manifest(kb_dir)


def test_duplicate_source_path_is_rejected(kb_dir: Path) -> None:
    manifest_path = kb_dir / "manifest.yaml"
    text = manifest_path.read_text(encoding="utf-8").replace(
        "path: sources/json.html", "path: sources/http.md"
    )
    manifest_path.write_text(text, encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(kb_dir)
