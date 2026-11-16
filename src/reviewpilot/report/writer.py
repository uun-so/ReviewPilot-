"""Canonical result.json, human-readable report.md, and trace.jsonl."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterable

from reviewpilot.domain import CheckResult, Claim

_VERDICT_LABELS = {
    "supported": "✅ 支持",
    "conflict": "❌ 与证据冲突",
    "uncertain": "⚠️ 存疑",
}
_REASON_LABELS = {
    "opinion": "观点",
    "prediction": "预测",
    "definition": "定义",
    "rhetoric": "修辞",
    "code": "代码",
    "other": "其他不可判定",
    "anchor_failed": "原文锚定失败",
    "extraction_failed": "主张抽取失败",
}


def _blockquote(text: str, prefix: str) -> list[str]:
    lines = text.splitlines() or [""]
    return [prefix + line for line in lines]


def _table_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(result: CheckResult) -> str:
    summary = result.summary
    lines: list[str] = [
        "# ReviewPilot 核验报告",
        "",
        f"- **文章**：`{result.run.article.path}`",
        f"- **知识库**：{result.run.kb.name} `{result.run.kb.version}`",
        f"- **模型**：判定 `{result.run.models.judge}` / 校验 `{result.run.models.verifier}`",
        (
            f"- **结论**：{summary.claims_total} 条主张 —— 支持 {summary.supported}，"
            f"冲突 {summary.conflict}，存疑 {summary.uncertain}；未核验 {summary.unverified} 句"
        ),
        "",
        "## 逐句结论",
        "",
    ]

    claims_by_sentence: dict[str, list[Claim]] = {}
    for claim in result.claims:
        for sentence_id in claim.sentence_ids:
            claims_by_sentence.setdefault(sentence_id, []).append(claim)

    for sentence in result.sentences:
        sentence_claims = claims_by_sentence.get(sentence.sentence_id, [])
        if not sentence_claims:
            continue
        heading = f"（{sentence.heading_path}）" if sentence.heading_path else ""
        lines.append(f"### {sentence.sentence_id}{heading}")
        lines.append("")
        lines.extend(_blockquote(sentence.text, "> "))
        lines.append("")
        for claim in sentence_claims:
            label = _VERDICT_LABELS.get(claim.verdict, claim.verdict)
            lines.append(f"- **{label}**")
            lines.extend(_blockquote(claim.quote, "  > "))
            lines.append(f"  - 理由：{claim.reason}")
            for evidence in claim.evidence:
                relation = "反证" if evidence.relation == "contradicts" else "支持"
                used = "" if evidence.used_for_verdict else "（仅展示，未参与判定）"
                version = evidence.source_version or "版本未标注"
                lines.append(
                    f"  - {relation}证据：**{evidence.doc_title}**（{version}）{used}"
                )
                lines.extend(_blockquote(evidence.quote, "    > "))
            lines.append("")

    lines.extend(["## 未核验", ""])
    if result.unverified:
        lines.extend(["| 句子 | 原因 | 原文 |", "|---|---|---|"])
        for item in result.unverified:
            label = _REASON_LABELS.get(item.reason, item.reason)
            lines.append(
                f"| {item.sentence_id} | {label} | {_table_cell(item.text)} |"
            )
    else:
        lines.append("无。")
    lines.append("")

    lines.extend(
        [
            "## 运行元数据",
            "",
            f"- run_id：`{result.run.run_id}`",
            f"- created_at：{result.run.created_at}",
            f"- 文章 sha256：`{result.run.article.sha256}`",
            f"- KB manifest sha256：`{result.run.kb.manifest_sha256}`",
            f"- prompt_version：`{result.run.prompt_version}`",
            f"- code_version：`{result.run.code_version}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    result: CheckResult,
    run_dir: Path,
    *,
    article_path: Path | None = None,
    store_article: bool = True,
    trace_events: Iterable[dict] | None = None,
) -> dict[str, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    result_path = run_dir / "result.json"
    result_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths["result"] = result_path

    report_path = run_dir / "report.md"
    report_path.write_text(render_markdown(result), encoding="utf-8")
    paths["report"] = report_path

    if trace_events is not None:
        trace_path = run_dir / "trace.jsonl"
        with trace_path.open("w", encoding="utf-8") as handle:
            for event in trace_events:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        paths["trace"] = trace_path

    if store_article and article_path is not None:
        copy_path = run_dir / article_path.name
        shutil.copyfile(article_path, copy_path)
        paths["article"] = copy_path

    return paths
