# 0007. DeepSeek Responses API 与模型分工

- 状态：已接受
- 日期：2026-11-14
- 关联：[0004](0004-evidence-gates.md)、[0008](0008-fail-closed-idempotency.md)、[0011](0011-privacy-provider-boundary.md)

## 背景

判定模型需要在"只看证据"的约束下输出结构化结论，且成本要能支撑逐条主张的多次调用。Claude 方案的成本约 $1.2–3/篇；DeepSeek 的官方价格低一个数量级，但 API 形态不同：Chat Completions 只支持 `json_object`，不支持 `json_schema`；思考模式默认开启；没有 Batch API。

## 决策

1. 使用 DeepSeek **Responses API**（`https://api.deepseek.com`），通过 `text.format = {"type":"json_schema", ...}` 获得结构化输出；本地仍用 Pydantic 校验，失败重试一次。
2. 模型分工：
   - 主张抽取、检索式生成：`deepseek-flash`，`reasoning.effort="none"`。
   - 判定：`deepseek-v4-pro`，`reasoning.effort="none"`，`temperature=0`。
   - 独立校验：`deepseek-v4-pro`，`reasoning.effort="low"`（思考模式下 temperature 无效）。
3. 不使用 Chat Completions 的 `json_object` 作为主路径；它只保证合法 JSON，不保证 schema。保留为 Responses API 不可用时的回退方案。
4. 不使用严格工具调用 beta（`/beta`、`strict:true`）；Responses API 的 `json_schema` 已覆盖需求，避免 beta 端点。
5. 没有 Batch API：目录批处理通过并发实现，默认并发 8，可配置到 64；账户上限 Flash 2500 / Pro 500。
6. 成本提示：高峰为 UTC 工作日 01:00–04:00、06:00–10:00（北京时间 09:00–12:00、14:00–18:00），其余时间半价。默认配置约 $0.4–0.5/篇（非高峰），高峰翻倍。
7. 运行元数据记录供应商返回的模型标识；模型 ID 指向最新版本，供应商更新后需要重跑评测。

## 备选方案

- **Chat Completions + `json_object`**：更保守，但没有 schema 保证，解析失败率更高；作为回退。
- **严格工具调用 beta**：schema 保证好，但依赖 beta 端点；v1 不采用。
- **全部使用 `deepseek-flash`**：成本约 $0.1/篇，但判定质量风险最高；作为评测对照。
- **全部使用 `deepseek-v4-pro` + `effort=high`**：约 $1–2/篇，速度更慢；除非评测证明必要，否则不默认。

## 后果

- 成本不再是主要约束，质量与可复现性成为主要约束。
- Responses API 是较新的接口；适配器必须隔离，便于回退或用 provider 抽象切换（[0011](0011-privacy-provider-boundary.md)）。
- 思考模式默认开启，任何调用都必须显式设置 `reasoning.effort`，否则成本和延迟会超出预期。
- 实测中模型偶尔在 `json_schema` 模式下仍返回 ```json 代码围栏。provider 只在解析前剥离围栏和首尾杂质，随后仍走 Pydantic schema 校验；这不是放宽闸门，而是对模型输出格式的归一化。
