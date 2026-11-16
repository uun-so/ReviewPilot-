"""Generate blind labeling templates from gold articles.

This script does NOT call an LLM and does NOT include system verdicts. It
segments each article into sentences, then writes ``labels.yaml`` with empty
``human_verdict`` fields and a human-readable ``labeling-sheet.md``.

Run:
    python scripts/prepare_gold_labels.py [--force]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from reviewpilot.claims.sentences import segment_document
from reviewpilot.pipeline import load_article

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "eval" / "gold"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="覆盖已有 labels.yaml")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    cases = sorted(path for path in GOLD.iterdir() if (path / "article.md").exists())
    if not cases:
        raise SystemExit("没有找到 eval/gold/*/article.md")

    sheet_lines = [
        "# ReviewPilot 盲标表",
        "",
        "> 标注时不要查看任何系统结论。判断只相对于 `kb/demo`，不要使用外部知识。",
        "",
        "> 本表只列出本次生成 `labels.yaml` 的 case；已有标注不会被覆盖。",
        "",
        "**结论取值**：`supported`（KB 明确支持）/ `conflict`（KB 明确反驳）/ "
        "`uncertain`（KB 未覆盖或证据不足）/ `non_claim`（观点、预测、定义、修辞，不是可判定主张）。",
        "",
        "把结论填到每个 case 的 `labels.yaml` 的 `human_verdict` 字段，然后运行：",
        "",
        "```bash",
        "reviewpilot eval --gold eval/gold --kb kb/demo",
        "```",
        "",
    ]

    total = 0
    for case_dir in cases:
        case_name = case_dir.name
        labels_path = case_dir / "labels.yaml"
        if labels_path.exists() and not args.force:
            print(f"跳过 {labels_path}（已存在；加 --force 覆盖）")
            continue

        article_path = case_dir / "article.md"
        document = load_article(article_path)
        sentences = segment_document(document)

        claims = []
        for index, sentence in enumerate(sentences, start=1):
            claims.append(
                {
                    "id": f"{case_name}-{index:03d}",
                    "quote": sentence.text,
                    "char_start": sentence.char_start,
                    "char_end": sentence.char_end,
                    "human_verdict": "",
                    "note": "",
                }
            )

        labels = {
            "case": case_name,
            "article": "article.md",
            "claims": claims,
        }
        labels_path.write_text(
            yaml.safe_dump(labels, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        total += len(claims)

        sheet_lines.extend([f"## {case_name}", "", "| ID | 主张（逐字） | 人工结论 | 备注 |", "|---|---|---|---|"])
        for claim in claims:
            sheet_lines.append(
                f"| {claim['id']} | {_cell(claim['quote'])} |  |  |"
            )
        sheet_lines.append("")

    (GOLD / "labeling-sheet.md").write_text("\n".join(sheet_lines), encoding="utf-8")
    print(f"生成 {total} 条待标主张，表：{GOLD / 'labeling-sheet.md'}")


if __name__ == "__main__":
    main()
