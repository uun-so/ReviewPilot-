"""M3 gold-set evaluation harness.

The harness is deliberately fail-closed:
- It refuses to run while any ``human_verdict`` is blank or invalid.
- It matches gold claims to system claims by character-span overlap.
- The gate is false-support == 0 (plus agreement/recall/evidence thresholds).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from reviewpilot.config import AppConfig
from reviewpilot.domain import CheckResult, Claim
from reviewpilot.ingest.loader import load_document
from reviewpilot.ingest.manifest import load_manifest
from reviewpilot.llm.provider import LLMProvider
from reviewpilot.pipeline import CheckOptions, run_check

ALLOWED_VERDICTS = {"supported", "conflict", "uncertain", "non_claim"}
CHECKABLE = {"supported", "conflict", "uncertain"}
MATCH_THRESHOLD = 0.5


class EvalError(RuntimeError):
    """Gold-set or evaluation configuration error."""


class GoldClaim(BaseModel):
    id: str
    quote: str
    char_start: int | None = None
    char_end: int | None = None
    human_verdict: str = ""
    note: str = ""


class GoldCaseModel(BaseModel):
    case: str
    article: str = "article.md"
    claims: list[GoldClaim]


@dataclass(frozen=True)
class LoadedGoldCase:
    case: str
    article_path: Path
    article_text: str
    claims: list[GoldClaim]


def load_gold_cases(gold_dir: Path) -> list[LoadedGoldCase]:
    gold_dir = gold_dir.resolve()
    if not gold_dir.exists():
        raise EvalError(f"金标目录不存在：{gold_dir}")

    cases: list[LoadedGoldCase] = []
    unlabeled: list[str] = []

    for labels_path in sorted(gold_dir.glob("*/labels.yaml")):
        try:
            raw = yaml.safe_load(labels_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise EvalError(f"无法读取 {labels_path}：{exc}") from exc
        try:
            model = GoldCaseModel.model_validate(raw)
        except ValidationError as exc:
            raise EvalError(f"{labels_path} 格式无效：{exc}") from exc

        article_path = (labels_path.parent / model.article).resolve()
        if not article_path.is_file():
            raise EvalError(f"金标文章不存在：{article_path}")
        try:
            article_text = article_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise EvalError(f"金标文章不是 UTF-8：{article_path}") from exc

        normalized: list[GoldClaim] = []
        for claim in model.claims:
            if not claim.quote.strip():
                raise EvalError(f"{labels_path}: {claim.id} 的 quote 为空")
            if claim.char_start is None or claim.char_end is None:
                position = article_text.find(claim.quote)
                if position == -1:
                    raise EvalError(
                        f"{labels_path}: {claim.id} 的 quote 在文章中找不到，请重新生成标注表"
                    )
                claim = claim.model_copy(
                    update={
                        "char_start": position,
                        "char_end": position + len(claim.quote),
                    }
                )
            elif article_text[claim.char_start : claim.char_end] != claim.quote:
                raise EvalError(
                    f"{labels_path}: {claim.id} 的 quote 与 char_start/end 不一致，"
                    "请重新生成标注表"
                )

            if claim.human_verdict not in ALLOWED_VERDICTS:
                if not claim.human_verdict:
                    unlabeled.append(claim.id)
                else:
                    raise EvalError(
                        f"{labels_path}: {claim.id} 的 human_verdict={claim.human_verdict!r} 无效；"
                        f"允许值：{sorted(ALLOWED_VERDICTS)}"
                    )
            normalized.append(claim)

        cases.append(
            LoadedGoldCase(
                case=model.case,
                article_path=article_path,
                article_text=article_text,
                claims=normalized,
            )
        )

    if not cases:
        raise EvalError(f"没有找到任何 */labels.yaml：{gold_dir}")
    if unlabeled:
        preview = "、".join(unlabeled[:10])
        more = "" if len(unlabeled) <= 10 else f" 等 {len(unlabeled)} 条"
        raise EvalError(
            f"还有 {len(unlabeled)} 条主张未标注：{preview}{more}。"
            "请填写对应 labels.yaml 的 human_verdict 后重跑。"
        )
    return cases


def _overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def match_claims(
    gold_claims: list[GoldClaim], system_claims: list[Claim]
) -> tuple[dict[str, Claim], list[Claim]]:
    """Greedy one-to-one matching by span overlap; returns (matches, ungraded)."""
    used: set[int] = set()
    matches: dict[str, Claim] = {}

    for gold in gold_claims:
        best_index: int | None = None
        best_score = 0.0
        for index, system in enumerate(system_claims):
            if index in used:
                continue
            overlap = _overlap(
                gold.char_start or 0,
                gold.char_end or 0,
                system.char_start,
                system.char_end,
            )
            if overlap <= 0:
                continue
            score = overlap / max(1, min(len(gold.quote), len(system.quote)))
            if score > best_score:
                best_score = score
                best_index = index
        if best_index is not None and best_score >= MATCH_THRESHOLD:
            matches[gold.id] = system_claims[best_index]
            used.add(best_index)

    ungraded = [claim for index, claim in enumerate(system_claims) if index not in used]
    return matches, ungraded


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def compute_case_metrics(
    case: LoadedGoldCase,
    result: CheckResult,
    doc_texts: dict[str, str],
) -> dict[str, Any]:
    matches, ungraded = match_claims(case.claims, result.claims)
    false_support = 0
    ungraded_support = 0
    matched_checkable = 0
    missed_checkable = 0
    supported_total = 0
    supported_agreed = 0
    conflict_total = 0
    conflict_hit = 0
    mismatches: list[dict[str, Any]] = []

    for gold in case.claims:
        system = matches.get(gold.id)
        is_checkable = gold.human_verdict in CHECKABLE
        if is_checkable:
            if system is None:
                missed_checkable += 1
                mismatches.append(
                    {
                        "type": "missed",
                        "gold_id": gold.id,
                        "gold_quote": gold.quote,
                        "human_verdict": gold.human_verdict,
                    }
                )
            else:
                matched_checkable += 1

        if gold.human_verdict == "supported":
            supported_total += 1
            if system is not None and system.verdict == "supported":
                supported_agreed += 1
            elif system is not None:
                mismatches.append(
                    {
                        "type": "supported_disagreement",
                        "gold_id": gold.id,
                        "gold_quote": gold.quote,
                        "human_verdict": gold.human_verdict,
                        "system_verdict": system.verdict,
                        "system_quote": system.quote,
                    }
                )

        if gold.human_verdict == "conflict":
            conflict_total += 1
            if system is not None and system.verdict == "conflict":
                conflict_hit += 1
            elif system is not None and system.verdict != "supported":
                # A system "supported" verdict is reported once below as a
                # false_support, which is the more severe finding.
                mismatches.append(
                    {
                        "type": "conflict_miss",
                        "gold_id": gold.id,
                        "gold_quote": gold.quote,
                        "human_verdict": gold.human_verdict,
                        "system_verdict": system.verdict,
                        "system_quote": system.quote,
                    }
                )

        if (
            system is not None
            and system.verdict == "supported"
            and gold.human_verdict in {"uncertain", "conflict", "non_claim"}
        ):
            false_support += 1
            mismatches.append(
                {
                    "type": "false_support",
                    "gold_id": gold.id,
                    "gold_quote": gold.quote,
                    "human_verdict": gold.human_verdict,
                    "system_verdict": system.verdict,
                    "system_quote": system.quote,
                }
            )

    for system in ungraded:
        if system.verdict == "supported":
            ungraded_support += 1
            mismatches.append(
                {
                    "type": "ungraded_support",
                    "system_quote": system.quote,
                    "system_verdict": system.verdict,
                }
            )
        else:
            mismatches.append(
                {
                    "type": "ungraded",
                    "system_quote": system.quote,
                    "system_verdict": system.verdict,
                }
            )

    evidence_total = 0
    evidence_valid = 0
    for claim in result.claims:
        for evidence in claim.evidence:
            evidence_total += 1
            document_text = doc_texts.get(evidence.doc_id)
            if (
                document_text is not None
                and document_text[evidence.char_start : evidence.char_end] == evidence.quote
            ):
                evidence_valid += 1
            else:
                mismatches.append(
                    {
                        "type": "evidence_invalid",
                        "claim_id": claim.claim_id,
                        "doc_id": evidence.doc_id,
                        "quote": evidence.quote,
                    }
                )

    uncertain_total = sum(
        1 for gold in case.claims if gold.human_verdict == "uncertain"
    )
    checkable_total = supported_total + conflict_total + uncertain_total
    return {
        "case": case.case,
        "gold_total": len(case.claims),
        "system_total": len(result.claims),
        "matched": len(matches),
        "false_support": false_support,
        "ungraded_support": ungraded_support,
        "missed_checkable": missed_checkable,
        "matched_checkable": matched_checkable,
        "checkable_total": checkable_total,
        "supported_total": supported_total,
        "supported_agreed": supported_agreed,
        "supported_agreement": _ratio(supported_agreed, supported_total),
        "conflict_total": conflict_total,
        "conflict_hit": conflict_hit,
        "conflict_recall": _ratio(conflict_hit, conflict_total),
        "coverage": _ratio(matched_checkable, checkable_total),
        "evidence_total": evidence_total,
        "evidence_valid": evidence_valid,
        "evidence_exactness": _ratio(evidence_valid, evidence_total),
        "mismatches": mismatches[:200],
    }


def aggregate_metrics(case_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    count_keys = (
        "gold_total",
        "system_total",
        "matched",
        "false_support",
        "ungraded_support",
        "missed_checkable",
        "matched_checkable",
        "checkable_total",
        "supported_total",
        "supported_agreed",
        "conflict_total",
        "conflict_hit",
        "evidence_total",
        "evidence_valid",
    )
    totals = {
        key: sum(item[key] for item in case_metrics)
        for key in count_keys
    }
    totals["supported_agreement"] = _ratio(
        totals["supported_agreed"], totals["supported_total"]
    )
    totals["conflict_recall"] = _ratio(
        totals["conflict_hit"], totals["conflict_total"]
    )
    totals["coverage"] = _ratio(
        totals["matched_checkable"], totals["checkable_total"]
    )
    totals["evidence_exactness"] = _ratio(
        totals["evidence_valid"], totals["evidence_total"]
    )
    return totals


def evaluate_gate(aggregate: dict[str, Any]) -> tuple[bool, dict[str, bool], list[str]]:
    checks = {
        "no_false_support": aggregate["false_support"] == 0,
        "no_ungraded_support": aggregate["ungraded_support"] == 0,
        "supported_agreement>=0.95": (
            aggregate["supported_total"] > 0
            and aggregate["supported_agreement"] >= 0.95
        ),
        "conflict_recall>=0.80": (
            aggregate["conflict_total"] > 0
            and aggregate["conflict_recall"] >= 0.80
        ),
        "evidence_exactness==1.0": (
            aggregate["evidence_total"] > 0
            and aggregate["evidence_exactness"] >= 1.0
        ),
    }
    reasons = [name for name, passed in checks.items() if not passed]
    if aggregate["supported_total"] == 0:
        reasons.append("金标集缺少 supported 样本")
    if aggregate["conflict_total"] == 0:
        reasons.append("金标集缺少 conflict 样本")
    return all(checks.values()), checks, reasons


def _load_kb_documents(kb_dir: Path) -> tuple[dict[str, str], dict[str, str]]:
    loaded = load_manifest(kb_dir)
    texts: dict[str, str] = {}
    for source in loaded.sources:
        document = load_document(source)
        texts[document.doc_id] = document.text
    kb_meta = {
        "name": loaded.manifest.name,
        "version": loaded.manifest.version,
        "manifest_sha256": loaded.manifest_sha256,
    }
    return texts, kb_meta


def _render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    gate = report["gate"]
    lines = [
        "# ReviewPilot 金标评测",
        "",
        f"- created_at：{report['created_at']}",
        f"- KB：{report['kb']['name']} `{report['kb']['version']}`",
        f"- 门槛：{'通过' if gate['passed'] else '未通过'}",
        "",
        "## 汇总",
        "",
        "| 指标 | 值 |",
        "|---|---:|",
        f"| 金标主张 | {aggregate['gold_total']} |",
        f"| 系统主张 | {aggregate['system_total']} |",
        f"| 匹配 | {aggregate['matched']} |",
        f"| 假支持 | {aggregate['false_support']} |",
        f"| 未匹配的支持 | {aggregate['ungraded_support']} |",
        f"| 漏掉的可判定主张 | {aggregate['missed_checkable']} |",
        f"| 支持一致率 | {aggregate['supported_agreement']:.1%} "
        f"({aggregate['supported_agreed']}/{aggregate['supported_total']}) |",
        f"| 冲突召回 | {aggregate['conflict_recall']:.1%} "
        f"({aggregate['conflict_hit']}/{aggregate['conflict_total']}) |",
        f"| 覆盖率 | {aggregate['coverage']:.1%} |",
        f"| 证据逐字有效 | {aggregate['evidence_exactness']:.1%} "
        f"({aggregate['evidence_valid']}/{aggregate['evidence_total']}) |",
        "",
        "## 门槛检查",
        "",
        "| 检查 | 结果 |",
        "|---|---|",
    ]
    for name, passed in gate["checks"].items():
        lines.append(f"| {name} | {'✅' if passed else '❌'} |")
    if gate["reasons"]:
        lines.extend(["", "未通过原因：" + "；".join(gate["reasons"])])

    lines.extend(
        [
            "",
            "## 分 case",
            "",
            "| case | 金标 | 系统 | 匹配 | 假支持 | 未匹配支持 | 支持一致率 | 冲突召回 | 覆盖率 | 证据逐字 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for item in report["cases"]:
        lines.append(
            f"| {item['case']} | {item['gold_total']} | {item['system_total']} | "
            f"{item['matched']} | {item['false_support']} | {item['ungraded_support']} | "
            f"{item['supported_agreement']:.1%} | {item['conflict_recall']:.1%} | "
            f"{item['coverage']:.1%} | {item['evidence_exactness']:.1%} |"
        )

    lines.extend(["", "## 分歧明细", ""])
    any_mismatch = False
    for item in report["cases"]:
        for mismatch in item["mismatches"]:
            any_mismatch = True
            quote = mismatch.get("gold_quote") or mismatch.get("system_quote") or ""
            lines.append(
                f"- `{mismatch['type']}` "
                f"{mismatch.get('gold_id', '')}：{quote}"
            )
    if not any_mismatch:
        lines.append("无。")
    lines.append("")
    return "\n".join(lines)


def run_eval(
    gold_dir: Path,
    kb_dir: Path,
    config: AppConfig,
    provider: LLMProvider,
    out_dir: Path | None = None,
) -> tuple[dict[str, Any], Path, bool]:
    cases = load_gold_cases(gold_dir)
    doc_texts, kb_meta = _load_kb_documents(kb_dir)
    now = datetime.now(timezone.utc)
    eval_dir = (out_dir or Path("eval/runs")) / now.strftime("%Y%m%dT%H%M%SZ")
    eval_dir.mkdir(parents=True, exist_ok=True)

    case_metrics = []
    for case in cases:
        result, run_dir = run_check(
            CheckOptions(
                article_path=case.article_path,
                kb_dir=kb_dir,
                out_dir=eval_dir / "runs",
                config=config,
                provider=provider,
                concurrency=config.concurrency,
            )
        )
        metrics = compute_case_metrics(case, result, doc_texts)
        metrics["run_dir"] = str(run_dir)
        case_metrics.append(metrics)

    aggregate = aggregate_metrics(case_metrics)
    passed, checks, reasons = evaluate_gate(aggregate)
    report = {
        "schema_version": "1.0",
        "created_at": now.isoformat(timespec="seconds"),
        "kb": kb_meta,
        "gate": {"passed": passed, "checks": checks, "reasons": reasons},
        "aggregate": aggregate,
        "cases": case_metrics,
    }

    (eval_dir / "eval-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (eval_dir / "eval-report.md").write_text(
        _render_markdown(report), encoding="utf-8"
    )
    return report, eval_dir, passed
