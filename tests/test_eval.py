from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from reviewpilot.config import AppConfig
from reviewpilot.domain import (
    ArticleMeta,
    CheckResult,
    Claim,
    Evidence,
    KbMeta,
    ModelMeta,
    RunMeta,
    Summary,
)
from reviewpilot.eval import (
    EvalError,
    GoldClaim,
    LoadedGoldCase,
    compute_case_metrics,
    evaluate_gate,
    load_gold_cases,
    match_claims,
    run_eval,
)
from reviewpilot.index.fts import build_index

from tests.fakes import FakeProvider

ARTICLE = "AAAA. BBBB. CCCC. DDDD. EEEE."
DOC_TEXT = "AAAA. BBBB. CCCC."


def _claim(
    claim_id: str,
    quote: str,
    start: int,
    end: int,
    verdict: str,
    evidence: list[Evidence] | None = None,
) -> Claim:
    return Claim(
        claim_id=claim_id,
        quote=quote,
        char_start=start,
        char_end=end,
        sentence_ids=["s1"],
        verdict=verdict,
        reason="",
        evidence=evidence or [],
        gates={"schema": "pass", "quote": "pass", "entailment": "pass"},
    )


def _result(claims: list[Claim]) -> CheckResult:
    return CheckResult(
        run=RunMeta(
            run_id="r",
            created_at="2026-11-14T00:00:00+00:00",
            article=ArticleMeta(path="a.md", sha256="x", char_count=len(ARTICLE)),
            kb=KbMeta(name="kb", version="1", manifest_sha256="x"),
            models=ModelMeta(
                judge="m",
                verifier="m",
                judge_effort="none",
                verifier_effort="low",
            ),
            prompt_version="p",
            code_version="c",
        ),
        summary=Summary(
            claims_total=len(claims),
            supported=sum(1 for c in claims if c.verdict == "supported"),
            conflict=sum(1 for c in claims if c.verdict == "conflict"),
            uncertain=sum(1 for c in claims if c.verdict == "uncertain"),
            unverified=0,
        ),
        sentences=[],
        claims=claims,
        unverified=[],
    )


def _case(claims: list[GoldClaim]) -> LoadedGoldCase:
    return LoadedGoldCase(
        case="case",
        article_path=Path("article.md"),
        article_text=ARTICLE,
        claims=claims,
    )


def test_match_and_metrics() -> None:
    gold_claims = [
        GoldClaim(id="g1", quote="AAAA.", char_start=0, char_end=5, human_verdict="supported"),
        GoldClaim(id="g2", quote="BBBB.", char_start=6, char_end=11, human_verdict="conflict"),
        GoldClaim(id="g3", quote="CCCC.", char_start=12, char_end=17, human_verdict="uncertain"),
        GoldClaim(id="g4", quote="DDDD.", char_start=18, char_end=23, human_verdict="non_claim"),
    ]
    claims = [
        _claim(
            "c1",
            "AAAA.",
            0,
            5,
            "supported",
            [
                Evidence(
                    doc_id="doc",
                    doc_title="Doc",
                    source_path="doc.md",
                    quote="AAAA.",
                    char_start=0,
                    char_end=5,
                    relation="supports",
                )
            ],
        ),
        _claim(
            "c2",
            "BBBB.",
            6,
            11,
            "conflict",
            [
                Evidence(
                    doc_id="doc",
                    doc_title="Doc",
                    source_path="doc.md",
                    quote="BBBB.",
                    char_start=6,
                    char_end=11,
                    relation="contradicts",
                )
            ],
        ),
        _claim("c3", "CCCC.", 12, 17, "supported"),
        _claim("c4", "DDDD.", 18, 23, "uncertain"),
        _claim("c5", "EEEE.", 24, 29, "supported"),
    ]

    matches, ungraded = match_claims(gold_claims, claims)
    assert set(matches) == {"g1", "g2", "g3", "g4"}
    assert [claim.claim_id for claim in ungraded] == ["c5"]

    metrics = compute_case_metrics(_case(gold_claims), _result(claims), {"doc": DOC_TEXT})
    assert metrics["false_support"] == 1  # c3 supported vs gold uncertain
    assert metrics["ungraded_support"] == 1  # c5
    assert metrics["supported_agreement"] == 1.0
    assert metrics["conflict_recall"] == 1.0
    assert metrics["coverage"] == 1.0
    assert metrics["evidence_total"] == 2
    assert metrics["evidence_valid"] == 2
    assert metrics["evidence_exactness"] == 1.0


def test_evidence_exactness_failure() -> None:
    gold = [GoldClaim(id="g1", quote="AAAA.", char_start=0, char_end=5, human_verdict="supported")]
    bad = Evidence(
        doc_id="doc",
        doc_title="Doc",
        source_path="doc.md",
        quote="NOT-IN-DOC",
        char_start=0,
        char_end=5,
        relation="supports",
    )
    metrics = compute_case_metrics(
        _case(gold), _result([_claim("c1", "AAAA.", 0, 5, "supported", [bad])]), {"doc": DOC_TEXT}
    )
    assert metrics["evidence_total"] == 1
    assert metrics["evidence_valid"] == 0
    assert metrics["evidence_exactness"] == 0.0


def test_gate_requires_samples_and_zero_false_support() -> None:
    base = {
        "false_support": 0,
        "ungraded_support": 0,
        "supported_total": 10,
        "supported_agreement": 0.96,
        "conflict_total": 5,
        "conflict_recall": 0.8,
        "evidence_total": 10,
        "evidence_exactness": 1.0,
    }
    passed, checks, reasons = evaluate_gate(base)
    assert passed
    assert all(checks.values())

    base["false_support"] = 1
    passed, _, reasons = evaluate_gate(base)
    assert not passed
    assert "no_false_support" in reasons

    base.update(false_support=0, supported_total=0, supported_agreement=0.0)
    passed, _, reasons = evaluate_gate(base)
    assert not passed
    assert "金标集缺少 supported 样本" in reasons


def _write_labels(directory: Path, verdicts: list[str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "article.md").write_text(ARTICLE, encoding="utf-8")
    labels = {
        "case": "case",
        "article": "article.md",
        "claims": [
            {"id": f"g{i + 1}", "quote": quote, "human_verdict": verdict}
            for i, (quote, verdict) in enumerate(
                zip(["AAAA.", "BBBB."], verdicts, strict=True)
            )
        ],
    }
    (directory / "labels.yaml").write_text(
        yaml.safe_dump(labels, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def test_unlabeled_gold_is_rejected(tmp_path: Path) -> None:
    _write_labels(tmp_path / "case", ["", ""])
    with pytest.raises(EvalError, match="未标注"):
        load_gold_cases(tmp_path)


def test_load_gold_fills_missing_spans(tmp_path: Path) -> None:
    _write_labels(tmp_path / "case", ["supported", "uncertain"])
    cases = load_gold_cases(tmp_path)
    assert len(cases) == 1
    first = cases[0].claims[0]
    assert (first.char_start, first.char_end) == (0, 5)


def test_run_eval_writes_report(kb_dir: Path, tmp_path: Path) -> None:
    article = tmp_path / "gold" / "case" / "article.md"
    article.parent.mkdir(parents=True)
    article.write_text("HTTPConnection 默认超时为 30 秒。\n", encoding="utf-8")
    labels = {
        "case": "case",
        "article": "article.md",
        "claims": [
            {
                "id": "g1",
                "quote": "HTTPConnection 默认超时为 30 秒。",
                "human_verdict": "supported",
            }
        ],
    }
    (article.parent / "labels.yaml").write_text(
        yaml.safe_dump(labels, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    build_index(kb_dir)

    def handler(**kwargs):
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
                {"input_tokens": 1, "output_tokens": 1},
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
                {"input_tokens": 1, "output_tokens": 1},
            )
        if kwargs["schema_name"] == "claim_verification":
            return (
                {"verdict": "supported", "reason": "引用直接支持"},
                {"input_tokens": 1, "output_tokens": 1},
            )
        raise AssertionError(kwargs["schema_name"])

    report, eval_dir, passed = run_eval(
        tmp_path / "gold",
        kb_dir,
        AppConfig(kb=kb_dir, concurrency=1),
        FakeProvider(handler),
        tmp_path / "eval",
    )
    assert report["aggregate"]["false_support"] == 0
    assert report["aggregate"]["supported_agreement"] == 1.0
    assert report["aggregate"]["evidence_exactness"] == 1.0
    assert passed is False  # no conflict sample yet
    assert (eval_dir / "eval-report.json").exists()
    assert (eval_dir / "eval-report.md").exists()
