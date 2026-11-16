from pathlib import Path

from typer.testing import CliRunner

from reviewpilot.cli import app

runner = CliRunner()


def test_help_exits_zero() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "reviewpilot" in result.output.lower()


def test_check_is_still_a_stub() -> None:
    result = runner.invoke(app, ["check", "article.md"])
    assert result.exit_code == 3


def test_kb_index_and_inspect(kb_dir: Path) -> None:
    result = runner.invoke(app, ["kb", "index", "--kb", str(kb_dir)])
    assert result.exit_code == 0, result.output
    assert "索引完成" in result.output

    result = runner.invoke(app, ["kb", "inspect", "--kb", str(kb_dir)])
    assert result.exit_code == 0, result.output
    assert "test-kb" in result.output


def test_kb_index_missing_manifest(tmp_path: Path) -> None:
    result = runner.invoke(app, ["kb", "index", "--kb", str(tmp_path)])
    assert result.exit_code == 3
