# 盲标说明

这是 v0.1 的人工金标集：6 个 case、200 条主张，已全部完成盲标，v0.1 门槛通过。标注者只看主张、原文和知识库，不看系统结论；以下步骤保留用于未来扩充。

## 步骤

1. 打开 `labeling-sheet.md`，逐条阅读主张；或者在终端运行交互式标注：
   `python scripts/label_gold.py`（可加 `--case json-article` 分批）。
2. 在每个 case 的 `labels.yaml` 中填写 `human_verdict`：
   - `supported`：`kb/demo` 中有片段明确支持该主张；
   - `conflict`：`kb/demo` 中有片段明确反驳该主张；
   - `uncertain`：知识库未覆盖、证据不足，或需要外部知识；
   - `non_claim`：观点、预测、定义、修辞等不可判定内容。
3. 不要修改 `quote`、`char_start`、`char_end`。如果发现主张表缺失或重复，可以在 `labels.yaml` 末尾追加，并在 `note` 说明。
4. 标完后运行：

```bash
reviewpilot eval --gold eval/gold --kb kb/demo
```

## 重要约定

- 判断只相对于 `kb/demo`，不使用外部知识。现实中为真但 KB 没写的主张，应标 `uncertain`。
- 标题和代码块不进入句子切分，因此不在表中。
- 候选主张由句子切分生成，不是系统判定结果；标注是盲的。
- 金标结论是最终人工结论；与系统分歧的条目会在评测报告中列出，供复核。
