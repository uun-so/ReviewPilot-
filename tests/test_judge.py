from __future__ import annotations

import json
from typing import Any

from reviewpilot.claims.anchor import AnchoredClaim
from reviewpilot.config import ModelConfig
from reviewpilot.judge.judge import _version_tokens, judge_claim

from tests.fakes import FakeProvider

CHUNK_TEXT = "HTTPConnection timeout 是超时时间；默认值为 30 秒。"
DOC_TEXT = "# HTTP\n\n" + CHUNK_TEXT + "\n"
CHUNK_START = DOC_TEXT.index(CHUNK_TEXT)
CHUNK_END = CHUNK_START + len(CHUNK_TEXT)

RETRIEVED = [
    {
        "chunk_id": "sources/http.md#c0001",
        "doc_id": "sources/http.md",
        "ord": 1,
        "heading_path": "HTTP",
        "text": CHUNK_TEXT,
        "char_start": CHUNK_START,
        "char_end": CHUNK_END,
        "token_count": 20,
        "title": "HTTP",
        "source_path": "sources/http.md",
        "source_version": "3.13",
        "format": "markdown",
        "document_text": DOC_TEXT,
        "score": 0.0,
    }
]

CLAIM = AnchoredClaim(
    sentence_id="s1",
    quote="HTTPConnection 默认超时为 30 秒。",
    char_start=0,
    char_end=20,
)


def _provider(judge: dict[str, Any], verifier: dict[str, Any]) -> FakeProvider:
    def handler(**kwargs: Any):
        if kwargs["schema_name"] in {"claim_judgment", "claim_judgment_retry"}:
            return judge, {"input_tokens": 10, "output_tokens": 5}
        if kwargs["schema_name"] == "claim_verification":
            return verifier, {"input_tokens": 4, "output_tokens": 2}
        raise AssertionError(f"unexpected schema {kwargs['schema_name']}")

    return FakeProvider(handler)


def test_supported_path() -> None:
    provider = _provider(
        {
            "verdict": "supported",
            "basis_doc_id": "sources/http.md",
            "reason": "文档写明默认值 30 秒",
            "evidence": [
                {
                    "chunk_id": "sources/http.md#c0001",
                    "quote": "默认值为 30 秒。",
                    "relation": "supports",
                }
            ],
        },
        {"verdict": "supported", "reason": "引用直接支持"},
    )
    outcome = judge_claim(provider, CLAIM, RETRIEVED, ModelConfig())
    assert outcome.verdict == "supported"
    assert outcome.gates == {"schema": "pass", "quote": "pass", "entailment": "pass"}
    assert outcome.evidence[0].used_for_verdict is True
    assert outcome.usage["input_tokens"] == 14


def test_quote_gate_failure() -> None:
    provider = _provider(
        {
            "verdict": "supported",
            "basis_doc_id": "sources/http.md",
            "reason": "伪造引用",
            "evidence": [
                {
                    "chunk_id": "sources/http.md#c0001",
                    "quote": "这句话不在片段里。",
                    "relation": "supports",
                }
            ],
        },
        {"verdict": "supported", "reason": "不应被调用"},
    )
    outcome = judge_claim(provider, CLAIM, RETRIEVED, ModelConfig())
    assert outcome.verdict == "uncertain"
    assert outcome.gates["quote"] == "fail"
    assert len(provider.calls) == 2  # one repair retry, verifier not called


def test_verifier_disagreement() -> None:
    provider = _provider(
        {
            "verdict": "supported",
            "basis_doc_id": "sources/http.md",
            "reason": "看起来支持",
            "evidence": [
                {
                    "chunk_id": "sources/http.md#c0001",
                    "quote": "默认值为 30 秒。",
                    "relation": "supports",
                }
            ],
        },
        {"verdict": "insufficient", "reason": "引用没有提到超时"},
    )
    outcome = judge_claim(provider, CLAIM, RETRIEVED, ModelConfig())
    assert outcome.verdict == "uncertain"
    assert outcome.gates["entailment"] == "fail"
    assert "verifier_disagrees" in outcome.reason


def test_conflict_path() -> None:
    provider = _provider(
        {
            "verdict": "conflict",
            "basis_doc_id": "sources/http.md",
            "reason": "文档给出不同默认值",
            "evidence": [
                {
                    "chunk_id": "sources/http.md#c0001",
                    "quote": "默认值为 30 秒。",
                    "relation": "contradicts",
                }
            ],
        },
        {"verdict": "conflict", "reason": "引用直接反驳"},
    )
    outcome = judge_claim(provider, CLAIM, RETRIEVED, ModelConfig())
    assert outcome.verdict == "conflict"
    assert outcome.evidence[0].used_for_verdict is True


def test_supported_with_counter_evidence_becomes_conflict() -> None:
    provider = _provider(
        {
            "verdict": "supported",
            "basis_doc_id": "sources/http.md",
            "reason": "判定器误判为支持",
            "evidence": [
                {
                    "chunk_id": "sources/http.md#c0001",
                    "quote": "默认值为 30 秒。",
                    "relation": "contradicts",
                }
            ],
        },
        {"verdict": "conflict", "reason": "引用直接反驳"},
    )
    outcome = judge_claim(provider, CLAIM, RETRIEVED, ModelConfig())
    assert outcome.verdict == "conflict"
    assert "存在反证片段" in outcome.reason


def test_version_mismatch_short_circuits() -> None:
    provider = _provider({}, {})
    claim = AnchoredClaim(
        sentence_id="s1",
        quote="v2.0 的默认超时是 30 秒。",
        char_start=0,
        char_end=20,
    )
    outcome = judge_claim(provider, claim, RETRIEVED, ModelConfig())
    assert outcome.verdict == "uncertain"
    assert "no_matching_version" in outcome.reason
    assert provider.calls == []


def test_version_token_context() -> None:
    assert _version_tokens("`HTTPResponse.version` 在 HTTP/1.1 时是 11。") == []
    assert _version_tokens("在版本 3.13 中，ensure_ascii 默认为 True。") == ["3.13"]
    assert _version_tokens("v2.0 默认超时是 30 秒。") == ["2.0"]


def test_protocol_version_is_not_a_document_version() -> None:
    provider = _provider(
        {
            "verdict": "uncertain",
            "basis_doc_id": "",
            "reason": "证据不足",
            "evidence": [],
        },
        {},
    )
    claim = AnchoredClaim(
        sentence_id="s1",
        quote="`HTTPResponse.version` 在 HTTP/1.1 时是 11。",
        char_start=0,
        char_end=30,
    )
    outcome = judge_claim(provider, claim, RETRIEVED, ModelConfig())
    assert "no_matching_version" not in outcome.reason
    assert len(provider.calls) == 1


def test_quote_gate_retry_recovers() -> None:
    calls = {"judge": 0}

    def handler(**kwargs: Any):
        if kwargs["schema_name"] in {"claim_judgment", "claim_judgment_retry"}:
            calls["judge"] += 1
            quote = "这句话不在片段里。" if calls["judge"] == 1 else "默认值为 30 秒。"
            return (
                {
                    "verdict": "supported",
                    "basis_doc_id": "sources/http.md",
                    "reason": "文档写明默认值",
                    "evidence": [
                        {
                            "chunk_id": "sources/http.md#c0001",
                            "quote": quote,
                            "relation": "supports",
                        }
                    ],
                },
                {"input_tokens": 10, "output_tokens": 5},
            )
        if kwargs["schema_name"] == "claim_verification":
            return {"verdict": "supported", "reason": "引用直接支持"}, {
                "input_tokens": 4,
                "output_tokens": 2,
            }
        raise AssertionError(kwargs["schema_name"])

    outcome = judge_claim(FakeProvider(handler), CLAIM, RETRIEVED, ModelConfig())
    assert outcome.verdict == "supported"
    assert calls["judge"] == 2
    assert outcome.evidence[0].used_for_verdict is True


def test_no_retrieval_short_circuits() -> None:
    provider = _provider({}, {})
    outcome = judge_claim(provider, CLAIM, [], ModelConfig())
    assert outcome.verdict == "uncertain"
    assert "no_retrieval_results" in outcome.reason
    assert provider.calls == []


def test_prompt_contains_claim_and_chunk_id() -> None:
    provider = _provider(
        {
            "verdict": "uncertain",
            "basis_doc_id": "",
            "reason": "证据不足",
            "evidence": [],
        },
        {},
    )
    judge_claim(provider, CLAIM, RETRIEVED, ModelConfig())
    payload = json.loads(provider.calls[0]["input"])
    assert payload["claim"] == CLAIM.quote
    assert payload["chunks"][0]["chunk_id"] == "sources/http.md#c0001"
