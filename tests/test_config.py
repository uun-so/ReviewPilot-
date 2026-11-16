from pathlib import Path

from reviewpilot.config import AppConfig, load_config, stricter_sensitivity


def test_defaults() -> None:
    config = AppConfig()
    assert config.models.judge == "deepseek-v4-pro"
    assert config.models.verifier_effort == "low"
    assert config.concurrency == 4


def test_missing_default_file_yields_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = load_config()
    assert config.kb == Path("kb/demo")


def test_explicit_missing_file_raises(tmp_path: Path) -> None:
    try:
        load_config(tmp_path / "nope.yaml")
    except FileNotFoundError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected FileNotFoundError")


def test_relative_kb_resolves_against_config_dir(tmp_path: Path) -> None:
    config_path = tmp_path / "reviewpilot.yaml"
    config_path.write_text("kb: kb/demo\nconcurrency: 4\n", encoding="utf-8")
    config = load_config(config_path)
    assert config.concurrency == 4
    assert config.kb == (tmp_path / "kb" / "demo").resolve()


def test_stricter_sensitivity() -> None:
    assert stricter_sensitivity("public", "confidential") == "confidential"
    assert stricter_sensitivity("internal", "public") == "internal"
    assert stricter_sensitivity("public", "public") == "public"
