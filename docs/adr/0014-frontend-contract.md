# 0014. 前端技术栈与结果展示契约

- 状态：已接受
- 日期：2026-11-17
- 关联：[0012](0012-output-contract.md)、[0013](0013-web-api-job-model.md)

## 背景

`result.json` 是规范输出，`report.md` 是人读视图。Web UI 需要稳定地展示逐条结论、证据关系、闸门结果和未核验内容；如果前端解析 Markdown，展示层会与规范输出脱节。前端也不能接触 API Key 或直接选择任意 KB 路径。

## 决策

1. 前端使用 **React 19 + TypeScript + Vite**；`web/` 是独立的 npm 项目，构建产物 `web/dist` 由 FastAPI 静态托管。
2. 前端**按 `result.json` 的结构化字段渲染**（claims / sentences / evidence / unverified），不解析 `report.md`；报告 Markdown 只作为下载/审计视图。
3. 提交核验后使用轮询：`POST /api/checks` 返回 job id，前端每 1.5 秒 `GET /api/jobs/{id}`；成功后拉取 `/result`。
4. 证据展示必须区分 `supports` / `contradicts`，并显示 `used_for_verdict=false` 的「仅展示」标记；不把证据隐藏在折叠层里。
5. 前端只发送文章文本与 KB id；API Key、KB 根路径、文件系统路径都不进入浏览器状态。
6. 开发模式使用 Vite 的 `/api` 代理到 `127.0.0.1:8000`；生产模式同源，无需 CORS（CORS 仅放行本地 Vite 端口）。
7. 前端没有引入图表或 Markdown 渲染库；依赖面保持在 React + Vite + TS。
8. v2 的 Web UI 不提供 `--no-store-article` 等价开关；输入副本始终落在服务端 `runs/`。

## 备选方案

- **服务端 Jinja 模板**：依赖少，但交互（轮询、文件读取、动态证据）会变复杂；排除。
- **Next.js / SSR**：能力过剩，且引入 Node 服务端与 Python 服务端双运行时；排除。
- **Vue / Svelte**：同样可行；团队已有 React/TS 经验时 React 生态更稳；选择 React。
- **前端解析 `report.md`**：展示层与规范输出容易漂移；排除。
- **把前端打进 Python wheel**：会让 wheel 携带静态资源、需要前端构建链；v2 保持源码仓库内构建，API 无前端时仍可用。

## 后果

- 需要 Node/npm 构建前端；CLI 用户完全不受影响。
- 前端与 API 的契约是 `result.json` 字段；字段变更必须同步更新 `web/src/api.ts` 与 UI。
- 前端没有认证能力，安全边界仍由 localhost 绑定和后续的反向代理/认证负责。
- 结构化渲染让「证据 — 结论 — 闸门」的关系比 Markdown 更清晰，也更容易做后续 UI 迭代。
