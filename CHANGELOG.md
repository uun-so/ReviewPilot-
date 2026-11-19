# Changelog

## 0.2.2 — 2026-11-19

- `index.html` 响应强制 `Cache-Control: no-cache, no-store, must-revalidate`，避免部署后浏览器继续加载旧 bundle；`/assets/*` 的哈希文件仍可正常缓存。
- 页脚显示 `Web v0.2.2`，可直接确认浏览器加载的是哪一版前端。
- 新增 API 测试覆盖首页 no-cache 行为。
- 测试：50 项 Python + 1 项前端回归；0.2.2 wheel/sdist 已重建。

## 0.2.1 — 2026-11-19

- 修复前端轮询竞态：作业状态变为 `succeeded` 时，effect 清理把 `cancelled` 置为 `true`，导致结果请求返回后被丢弃，界面一直停在“正在加载结果…”。现在轮询与结果拉取拆成两个独立 effect。
- 结果加载失败时提供「重试」按钮，不再无限等待。
- 新增前端回归测试（Vitest + Testing Library），模拟 `queued → running → succeeded` 并断言结果渲染。
- 版本升至 0.2.1；Python 测试 49 项、前端测试 1 项。

## 0.2.0 — 2026-11-17

- **v2 Web/API**：新增 `reviewpilot_api`（FastAPI）与 React / TypeScript / Vite 前端，复用同一判定引擎。
- 单进程作业队列，一次只跑一个核验；每个作业内部并发默认 4，避免突破 DeepSeek 低余额并发上限。
- KB 白名单扫描、文章 200k 字符上限、`internal` / `confidential` KB 显式云端确认、默认仅监听 `127.0.0.1`。
- API：health / KB 列表与重建索引 / 提交核验 / 作业状态 / result.json / report.md；`/docs` 提供 OpenAPI。
- 前端：KB 选择、文件读取、轮询进度、逐条结论与证据展示、未核验表、结果下载。
- 新增 ADR 0013（Web API 与作业模型）、0014（前端契约）；测试增至 49 项。
- 产物：`reviewpilot-0.2.0` wheel/sdist；前端构建由 `npm --prefix web run build` 生成。

## 0.1.0 — 2026-11-15

- 6 篇 demo 文章 / 200 条金标全部完成人工盲标。
- v0.1 发布门槛通过：假支持 0，支持一致率 99.1%（114/115），冲突召回 98.0%（49/50），覆盖率 100%，证据逐字 100%。
- 发布评测在 `0.1.0` 上重跑并归档：`docs/eval/v0.1.0-2026-11-15.md`。
- 默认并发从 8 降到 4，`eval` 增加 `--concurrency`，适配低余额账户的并发上限。
- wheel/sdist 重新构建为 `0.1.0`。

## 0.0.1 — 2026-11-15

- **M0**：KB manifest 校验、Markdown/HTML/TXT 解析、结构感知切块、SQLite FTS5 + jieba 索引。
- **M1**：原子主张抽取与逐字字符锚定；锚定失败进入「未核验」。
- **M2**：单跳证据判定、逐字引用闸门、独立校验、版本门控、`result.json` / `report.md` / `trace.jsonl`。
- **M3**：60 条人工盲标金标与评测 harness；最终假支持 0，支持一致率、冲突召回、证据逐字有效率均为 100%。
- **M4**：wheel/sdist 打包、`py.typed`、全新 venv 快速开始验证、README/ADR/评测报告收尾。
- **v0.1 金标扩充**：已生成 6 篇 demo 文章 / 200 条候选主张；60 条已标注，140 条待人工盲标。
- **已知限制**：v0.1 发布门槛仍需完成 140 条盲标并重跑 200 条评测。
