"""Evidence-gated judgment: judge, quote gate, single-hop basis, verifier."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from reviewpilot.claims.anchor import AnchoredClaim, locate_quote
from reviewpilot.config import ModelConfig
from reviewpilot.domain import Evidence, JudgeResult, VerifyResult
from reviewpilot.llm.provider import LLMError, LLMProvider

JUDGE_INSTRUCTIONS = """\
你是证据核验器。你只能使用用户提供的知识库片段作为证据，禁止使用任何外部知识。

任务：判断主张是否被片段直接支持、直接反驳，或证据不足。
规则：
1. supported：至少一个片段直接支持主张；单独看该片段即可推出主张，不需要外部常识。
2. conflict：至少一个片段明确否定主张，或对同一属性给出不同的具体值。仅仅描述不同的实现机制、没有提到该属性、或给出更弱的陈述，都不算 conflict，应判 uncertain。
3. 省略可选参数、关键字参数或更简略的签名，不构成 conflict；只有明确否定或对同一属性给出不同具体值才是 conflict。
4. 区分“参数默认值”与“有效默认行为”：如果片段在某个条件下明确给出有效默认行为，而主张描述的正是该有效行为，应判 supported；不要因为参数本身默认值是 None/False 就判 conflict。
5. uncertain：片段不足以支持或反驳；需要跨文档综合；或需要外部知识。
6. quote 必须从片段中逐字复制，包括标点；不得改写、翻译或补全。
7. 判定所依据的证据必须来自同一篇文档（basis_doc_id）。如果片段来自多篇文档，选择一篇作为依据；其他文档的线索可以列出但不参与判定。
8. "没有提到"不是反驳；没有提到就是 uncertain。
9. 对版本相关主张，只使用 source_version 匹配的片段。
10. 如果主张给出具体数值或默认值，而片段只说明该值来自全局设置或其他机制、没有给出具体数值，不要判 conflict，应判 uncertain。
11. 只输出符合给定 JSON schema 的对象。
"""

VERIFIER_INSTRUCTIONS = """\
你是独立校验器。你只看到主张和判定所依据的引用片段。
任务：仅凭这些引用片段，判断主张是被直接支持、直接反驳，还是证据不足。
禁止使用外部知识。如果必须补充片段之外的事实才能推出主张，回答 insufficient。
只有当引用片段明确否定主张，或对同一属性给出不同的具体值时，才回答 conflict。
片段没有提到、只描述不同机制、或只给出更弱的陈述，都应回答 insufficient。
省略可选参数、关键字参数或更简略的签名，不构成 conflict。
区分“参数默认值”与“有效默认行为”：如果引用在某个条件下明确给出有效默认行为，而主张描述该有效行为，回答 supported，不要用参数默认值否定它。
只输出符合给定 JSON schema 的对象。
"""

T = TypeVar("T", bound=BaseModel)

_VERSION_V = re.compile(r"\bv(\d+(?:\.\d+)+)\b", re.I)
# Exclude protocol/URL-like numbers such as HTTP/1.1 or path/2.0.
_VERSION_NUM = re.compile(r"(?<![\w/])(\d+(?:\.\d+)+)\b")
_CODE_SPAN = re.compile(r"`[^`]*`")


@dataclass
class ClaimOutcome:
    verdict: str
    reason: str
    evidence: list[Evidence]
    gates: dict[str, str]
    usage: dict[str, int]


def _merge_usage(target: dict[str, int], extra: dict[str, int]) -> None:
    for key, value in extra.items():
        target[key] = target.get(key, 0) + value


def _version_tokens(quote: str) -> list[str]:
    tokens = [match.group(1) for match in _VERSION_V.finditer(quote)]
    if not tokens:
        # Ignore code identifiers such as ``HTTPResponse.version``; only an
        # explicit 版本/version context makes a bare number a doc version.
        stripped = _CODE_SPAN.sub("", quote)
        if re.search(r"版本|\bversion\b", stripped, re.I):
            tokens = [match.group(1) for match in _VERSION_NUM.finditer(stripped)]
    return list(dict.fromkeys(tokens))


def _version_matches(source_version: str | None, token: str) -> bool:
    if not source_version:
        return False
    return re.search(rf"(?<![\d.]){re.escape(token)}(?![\d.])", source_version) is not None


def _validated_call(
    provider: LLMProvider,
    *,
    model: str,
    instructions: str,
    user_input: str,
    schema_model: type[T],
    schema_name: str,
    effort: str,
    max_output_tokens: int,
    usage: dict[str, int],
) -> T | None:
    """Call once, retry once on schema mismatch; None means schema gate failed."""
    repair = instructions
    for attempt in range(2):
        data, call_usage = provider.complete_json(
            model=model,
            instructions=repair,
            input=user_input,
            schema=schema_model.model_json_schema(),
            schema_name=schema_name,
            effort=effort,
            max_output_tokens=max_output_tokens,
            temperature=0.0,
        )
        _merge_usage(usage, call_usage)
        try:
            return schema_model.model_validate(data)
        except ValidationError:
            if attempt == 1:
                return None
            repair = (
                instructions
                + "\n上一次输出不符合 schema。请只返回符合 schema 的 JSON，不要解释。"
            )
    return None


def _uncertain(
    reason: str,
    gates: dict[str, str],
    usage: dict[str, int],
    evidence: list[Evidence] | None = None,
) -> ClaimOutcome:
    return ClaimOutcome(
        verdict="uncertain",
        reason=reason,
        evidence=evidence or [],
        gates=gates,
        usage=usage,
    )


def _collect_evidence(
    judge: JudgeResult, retrieved: list[dict[str, Any]]
) -> tuple[list[Evidence], str, list[str]]:
    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in retrieved}
    valid_evidence: list[Evidence] = []
    invalid_quotes: list[str] = []

    for item in judge.evidence:
        chunk = chunk_by_id.get(item.chunk_id)
        quote = item.quote.strip()
        if chunk is None or not quote or quote not in chunk["text"]:
            invalid_quotes.append(quote or item.quote or "<empty>")
            continue
        span = locate_quote(
            chunk.get("document_text") or "",
            quote,
            hint_start=chunk["char_start"],
            hint_end=chunk["char_end"],
        )
        if span is None:
            invalid_quotes.append(quote)
            continue
        start, end = span
        valid_evidence.append(
            Evidence(
                doc_id=chunk["doc_id"],
                doc_title=chunk["title"],
                source_path=chunk["source_path"],
                source_version=chunk.get("source_version"),
                quote=quote,
                char_start=start,
                char_end=end,
                relation=item.relation,
                used_for_verdict=False,
                chunk_id=item.chunk_id,
            )
        )

    return valid_evidence, ("fail" if invalid_quotes else "pass"), invalid_quotes


def judge_claim(
    provider: LLMProvider,
    claim: AnchoredClaim,
    retrieved: list[dict[str, Any]],
    config: ModelConfig,
) -> ClaimOutcome:
    usage: dict[str, int] = {}

    if not retrieved:
        return _uncertain(
            "知识库没有检索到相关片段（no_retrieval_results）",
            {"schema": "skip", "quote": "skip", "entailment": "skip"},
            usage,
        )

    version_tokens = _version_tokens(claim.quote)
    if version_tokens:
        retrieved = [
            chunk
            for chunk in retrieved
            if any(_version_matches(chunk.get("source_version"), token) for token in version_tokens)
        ]
        if not retrieved:
            return _uncertain(
                "知识库中没有与主张版本匹配的文档（no_matching_version）",
                {"schema": "skip", "quote": "skip", "entailment": "skip"},
                usage,
            )

    payload = {
        "claim": claim.quote,
        "chunks": [
            {
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "title": chunk["title"],
                "source_version": chunk.get("source_version") or "",
                "section": chunk.get("heading_path") or "",
                "text": chunk["text"],
            }
            for chunk in retrieved
        ],
    }
    judge_input = json.dumps(payload, ensure_ascii=False, indent=2)
    judge = _validated_call(
        provider,
        model=config.judge,
        instructions=JUDGE_INSTRUCTIONS,
        user_input=judge_input,
        schema_model=JudgeResult,
        schema_name="claim_judgment",
        effort=config.judge_effort,
        max_output_tokens=2048,
        usage=usage,
    )
    if judge is None:
        return _uncertain(
            "判定输出不符合 schema（schema_gate_failed）",
            {"schema": "fail", "quote": "skip", "entailment": "skip"},
            usage,
        )

    valid_evidence, quote_gate, invalid_quotes = _collect_evidence(judge, retrieved)

    # One repair attempt for a verbatim-quote failure. The gate is not
    # relaxed: the retried evidence still goes through the same checks.
    if judge.verdict != "uncertain" and quote_gate == "fail" and invalid_quotes:
        repair_instructions = (
            JUDGE_INSTRUCTIONS
            + "\n上一次输出中的以下引用不是片段的逐字子串：\n"
            + "\n".join(f"- {quote[:200]}" for quote in invalid_quotes[:8])
            + "\n请重新判定，并从 chunk text 中逐字复制 quote"
            "（包括标点、反引号和列表符号）。"
        )
        repaired = _validated_call(
            provider,
            model=config.judge,
            instructions=repair_instructions,
            user_input=judge_input,
            schema_model=JudgeResult,
            schema_name="claim_judgment_retry",
            effort=config.judge_effort,
            max_output_tokens=2048,
            usage=usage,
        )
        if repaired is not None:
            judge = repaired
            valid_evidence, quote_gate, invalid_quotes = _collect_evidence(
                judge, retrieved
            )

    if judge.verdict == "uncertain":
        return _uncertain(
            judge.reason or "证据不足（judge_uncertain）",
            {"schema": "pass", "quote": quote_gate, "entailment": "skip"},
            usage,
            valid_evidence,
        )

    if quote_gate == "fail":
        return _uncertain(
            "证据引用未通过逐字校验（quote_gate_failed）",
            {"schema": "pass", "quote": "fail", "entailment": "skip"},
            usage,
            valid_evidence,
        )

    if not valid_evidence:
        return _uncertain(
            "没有可用的证据引用（quote_gate_failed）",
            {"schema": "pass", "quote": "fail", "entailment": "skip"},
            usage,
            [],
        )

    contradicts = [
        evidence for evidence in valid_evidence if evidence.relation == "contradicts"
    ]
    supports = [evidence for evidence in valid_evidence if evidence.relation == "supports"]

    reason = judge.reason
    if contradicts:
        # ADR 0002/0009: a validated direct counter-example wins over support.
        verdict = "conflict"
        basis_doc_id = (
            judge.basis_doc_id
            if any(evidence.doc_id == judge.basis_doc_id for evidence in contradicts)
            else contradicts[0].doc_id
        )
        if judge.verdict == "supported":
            reason = (reason + "（判定器给出支持，但存在反证片段）").strip()
    elif judge.verdict == "supported":
        if not supports:
            return _uncertain(
                "没有可用的支持引用（no_valid_supporting_evidence）",
                {"schema": "pass", "quote": "pass", "entailment": "skip"},
                usage,
                valid_evidence,
            )
        verdict = "supported"
        basis_doc_id = (
            judge.basis_doc_id
            if any(evidence.doc_id == judge.basis_doc_id for evidence in supports)
            else supports[0].doc_id
        )
    else:
        return _uncertain(
            "判定器给出冲突，但没有可用的反证引用（no_valid_counter_evidence）",
            {"schema": "pass", "quote": "pass", "entailment": "skip"},
            usage,
            valid_evidence,
        )

    used: list[Evidence] = []
    for evidence in valid_evidence:
        if evidence.doc_id == basis_doc_id:
            evidence.used_for_verdict = True
            used.append(evidence)
        else:
            evidence.used_for_verdict = False

    if not used:
        return _uncertain(
            "判定证据为空（empty_evidence）",
            {"schema": "pass", "quote": "pass", "entailment": "skip"},
            usage,
            valid_evidence,
        )

    basis = next(
        (evidence for evidence in used if evidence.doc_id == basis_doc_id), used[0]
    )
    verifier_payload = {
        "claim": claim.quote,
        "basis": {
            "doc_id": basis.doc_id,
            "title": basis.doc_title,
            "source_version": basis.source_version or "",
        },
        "evidence": [
            {"relation": evidence.relation, "quote": evidence.quote}
            for evidence in used
        ],
    }
    verifier = _validated_call(
        provider,
        model=config.verifier,
        instructions=VERIFIER_INSTRUCTIONS,
        user_input=json.dumps(verifier_payload, ensure_ascii=False, indent=2),
        schema_model=VerifyResult,
        schema_name="claim_verification",
        effort=config.verifier_effort,
        max_output_tokens=1024,
        usage=usage,
    )
    if verifier is None:
        for evidence in used:
            evidence.used_for_verdict = False
        return _uncertain(
            "独立校验输出不符合 schema（verifier_schema_failed）",
            {"schema": "pass", "quote": "pass", "entailment": "fail"},
            usage,
            valid_evidence,
        )

    if verifier.verdict != verdict:
        for evidence in used:
            evidence.used_for_verdict = False
        return _uncertain(
            f"独立校验未确认该结论（verifier_disagrees）：{verifier.reason}",
            {"schema": "pass", "quote": "pass", "entailment": "fail"},
            usage,
            valid_evidence,
        )

    return ClaimOutcome(
        verdict=verdict,
        reason=reason,
        evidence=valid_evidence,
        gates={"schema": "pass", "quote": "pass", "entailment": "pass"},
        usage=usage,
    )
