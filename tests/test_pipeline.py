from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from reviewpilot.cli import app
from reviewpilot.config import AppConfig
from reviewpilot.index.fts import build_index
from reviewpilot.pipeline import CheckOptions, run_check

from tests.fakes import FakeProvider

runner = CliRunner()


def _handler(**kwargs: Any):
    if kwargs["schema_name"] == "claim_extraction":
        sentences = json.loads(kwargs["input"])
        return (
            {
                "sentences": [
                    {
                        "sentence_id": sentence["sentence_id"],
                        "claims": [
                            {
                                "quote": sentence["text"],
                                "kind": "checkable",
                                "reason": "",
                            }
                        ],
                    }
                    for sentence in sentences
                ]
            },
            {"input_tokens": 10, "output_tokens": 5},
        )
    if kwargs["schema_name"] == "claim_judgment":
        payload = json.loads(kwargs["input"])
        chunk = payload["chunks"][0]
        return (
            {
                "verdict": "supported",
                "basis_doc_id": chunk["doc_id"],
                "reason": "文档写明默认值",
                "evidence": [
                    {
                        "chunk_id": chunk["chunk_id"],
                        "quote": "默认值为 30 秒。",
                        "relation": "supports",
                    }
                ],
            },
            {"input_tokens": 20, "output_tokens": 8},
        )
    if kwargs["schema_name"] == "claim_verification":
        return (
            {"verdict": "supported", "reason": "引用直接支持"},
            {"input_tokens": 5, "output_tokens": 2},
        )
    raise AssertionError(f"unexpected schema {kwargs['schema_name']}")


def test_end_to_end_pipeline(kb_dir: Path, tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_text("HTTPConnection 默认超时为 30 秒。\n", encoding="utf-8")
    build_index(kb_dir)

    result, run_dir = run_check(
        CheckOptions(
            article_path=article,
            kb_dir=kb_dir,
            out_dir=tmp_path / "runs",
            config=AppConfig(kb=kb_dir, concurrency=1),
            provider=FakeProvider(_handler),
            concurrency=1,
        )
    )

    assert result.summary.claims_total == 1
    assert result.summary.supported == 1
    claim = result.claims[0]
    assert claim.verdict == "supported"
    assert claim.evidence[0].doc_id == "sources/http.md"
    assert claim.evidence[0].used_for_verdict is True
    assert (run_dir / "result.json").exists()
    assert (run_dir / "report.md").exists()
    assert (run_dir / "trace.jsonl").exists()
    assert "支持" in (run_dir / "report.md").read_text(encoding="utf-8")
    saved = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert saved["schema_version"] == "1.0"
    assert saved["claims"][0]["gates"]["entailment"] == "pass"


def test_check_cli_supported(kb_dir: Path, tmp_path: Path, monkeypatch) -> None:
    article = tmp_path / "article.md"
    article.write_text("HTTPConnection 默认超时为 30 秒。\n", encoding="utf-8")
    build_index(kb_dir)
    fake = FakeProvider(_handler)
    monkeypatch.setattr("reviewpilot.cli.DeepSeekProvider", lambda: fake)

    result = runner.invoke(
        app,
        [
            "check",
            str(article),
            "--kb",
            str(kb_dir),
            "--out",
            str(tmp_path / "runs"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "核验完成" in result.output


def test_check_cli_no_claims(kb_dir: Path, tmp_path: Path, monkeypatch) -> None:
    article = tmp_path / "opinion.md"
    article.write_text("我认为这是最好的方案。\n", encoding="utf-8")
    build_index(kb_dir)

    def opinion_handler(**kwargs: Any):
        if kwargs["schema_name"] == "claim_extraction":
            sentences = json.loads(kwargs["input"])
            return (
                {
                    "sentences": [
                        {
                            "sentence_id": sentence["sentence_id"],
                            "claims": [
                                {
                                    "quote": sentence["text"],
                                    "kind": "opinion",
                                    "reason": "主观判断",
                                }
                            ],
                        }
                        for sentence in sentences
                    ]
                },
                {"input_tokens": 1, "output_tokens": 1},
            )
        raise AssertionError("judge should not run when there are no claims")

    fake = FakeProvider(opinion_handler)
    monkeypatch.setattr("reviewpilot.cli.DeepSeekProvider", lambda: fake)
    result = runner.invoke(
        app,
        [
            "check",
            str(article),
            "--kb",
            str(kb_dir),
            "--out",
            str(tmp_path / "runs"),
        ],
    )
    assert result.exit_code == 4, result.output
    assert "未抽取到可判定主张" in result.output
