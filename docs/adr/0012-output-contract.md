# 0012. 输出契约与退出码

- 状态：已接受
- 日期：2026-11-14
- 关联：[0002](0002-verdict-taxonomy.md)、[0003](0003-atomic-claims-anchors.md)、[0008](0008-fail-closed-idempotency.md)

## 背景

报告要同时服务三类消费者：作者（读 Markdown）、CI（看退出码）、评测与审计（读结构化结果）。如果只输出一份 Markdown，评测需要重新解析；如果只输出 JSON，作者无法快速定位。字符偏移和证据引用必须从一开始就存在，否则后期无法补。

## 决策

1. `result.json` 是**规范输出**，`report.md` 是它的视图；两者同源生成，不各自计算结论。
2. `result.json` 顶层字段：`schema_version`、`run`、`summary`、`sentences`、`claims`、`unverified`。
3. `run` 记录：`run_id`、`created_at`、文章路径/哈希/字符数、KB `name/version/manifest_sha256`、模型配置、`prompt_version`、`code_version`。
4. `claims[]` 记录：`claim_id`、`quote`（连续逐字原文，即主张本身）、`char_start/end`、`sentence_ids`、`verdict`、`reason`、`evidence[]`、`gates`、`usage`。`evidence[]` 包含 `doc_id`、`doc_title`、`source_path`、`source_version`、`quote`、`char_start/end`、`relation`、`used_for_verdict`、`chunk_id`（审计回溯用）。`claim` 不设独立的 `text` 字段，避免"展示文本是否被改写"的歧义。`sentences[]` 额外带 `claim_ids`，用于把句子与主张关联起来。
5. `unverified[]` 记录：`sentence_id`、`text`、`reason`（`opinion/prediction/definition/rhetoric/code/other`）。
6. 字符偏移是 Python 字符串下标，指向规范化文本；不是行号，也不是原始 HTML DOM 偏移。
7. `trace.jsonl` 逐次记录模型调用、检索、闸门结果和用量；不记录 API Key。
8. 退出码：0 无存疑无冲突；1 有存疑；2 有冲突；3 运行错误；4 未抽取到主张。冲突优先于存疑（同时存在时返回 2）。
9. schema 版本：向后兼容的字段增加升 minor；破坏性变更升 major。README 与 ADR 同步更新。
10. 所有枚举值使用英文小写，展示层负责中文化；避免把展示文案写进规范输出。

## 备选方案

- **只输出 Markdown**：评测和 CI 需要重新解析，且无法稳定携带偏移；排除。
- **只输出 JSON**：作者体验差，无法快速定位；排除。
- **报告与 JSON 各自计算**：容易出现两套结论；排除。

## 后果

- 评测、CI 和报告共享同一份事实来源；报告中的每个结论都能回链到 claim 和 evidence。
- schema 一旦发布就需要维护兼容性；新增字段优先，不轻易重命名。
- 退出码让 CI 可以按"有冲突"阻断发布，而把"有存疑"作为警告。
