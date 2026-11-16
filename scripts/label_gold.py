"""Interactive blind labeling for eval/gold/*/labels.yaml.

Usage:
    python scripts/label_gold.py [--case json-article]

Keys: s=supported, c=conflict, u=uncertain, n=non_claim, q=quit.
The script never calls the model and never shows system verdicts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "eval" / "gold"
CHOICES = {
    "s": "supported",
    "c": "conflict",
    "u": "uncertain",
    "n": "non_claim",
}
LABELS = {
    "supported": "KB 明确支持",
    "conflict": "KB 明确反驳",
    "uncertain": "KB 未覆盖/证据不足",
    "non_claim": "观点、预测、定义、修辞等非主张",
}


def _save(path: Path, data: dict) -> None:
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="只标注某个 case 目录名")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    files = sorted(GOLD.glob("*/labels.yaml"))
    if args.case:
        files = [path for path in files if path.parent.name == args.case]
    if not files:
        raise SystemExit("没有找到 labels.yaml")

    remaining = 0
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        changed = False
        for claim in data.get("claims", []):
            if claim.get("human_verdict") in LABELS:
                continue
            remaining += 1
            print()
            print(f"[{data.get('case', path.parent.name)}] {claim.get('id')}")
            print(f"  {claim.get('quote')}")
            print("  结论：" + "  ".join(f"[{key}] {value}" for key, value in LABELS.items()))
            while True:
                answer = input("  s/c/u/n，或 q 退出：").strip().lower()
                if answer in {"q", "quit"}:
                    if changed:
                        _save(path, data)
                        print(f"已写回 {path}")
                    print(f"已退出；本次会话共处理 {remaining} 条。")
                    return
                if answer in CHOICES:
                    claim["human_verdict"] = CHOICES[answer]
                    changed = True
                    _save(path, data)
                    break
                print("  请输入 s、c、u、n 或 q。")
        if changed:
            print(f"已写回 {path}")

    print()
    print("全部标注完成。下一步：")
    print("  reviewpilot eval --gold eval/gold --kb kb/demo")


if __name__ == "__main__":
    main()
