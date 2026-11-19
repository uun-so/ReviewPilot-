# 0013. Web API 边界与单进程作业模型

- 关联：[0007](0007-deepseek-api-model-tiering.md)、[0011](0011-privacy-provider-boundary.md)、[0012](0012-output-contract.md)

## 背景

v2 要给 v0.1 的判定引擎加 Web 前端。一次核验包含抽取、逐条检索、判定与独立校验，通常需要几分钟；DeepSeek 账户的并发上限可能很低（本项目实测低余额时只有 5）。同时，API Key、文章全文和 KB 片段都不能由浏览器直接接触；KB 路径也不能由请求任意指定。

## 决策

1. 新增 `reviewpilot_api` 包，FastAPI 只做 HTTP 适配，核验仍调用 `reviewpilot.pipeline.run_check`，不复制判定逻辑。
2. **单进程作业队列**：一个 worker 线程串行执行核验；每个作业内部使用配置并发（默认 4）。多个作业并行会成倍放大模型并发，v2 不采用。
3. **作业状态在内存，产物在磁盘**：完成后 `result.json` / `report.md` / `trace.jsonl` 落在 `runs/`；服务重启后历史作业列表清空，但磁盘结果保留。
4. **KB 白名单**：`KbRegistry` 只扫描 `REVIEWPILOT_KB_ROOT` 的直接子目录；目录名即 API 的 KB id，请求不能传路径，杜绝目录穿越。重建索引是显式 `POST /api/kbs/{id}/index`。
5. **默认只监听 `127.0.0.1`，v2 不做账号体系**；README 明确警告不要暴露到公网。需要远程访问时应先加认证/反向代理。
6. API Key 只从服务端环境变量读取；`/api/health` 只返回 `api_key_configured` 布尔值，不返回 Key。
7. `POST /api/checks` 接收文章文本（上限 200,000 字符）；`internal` / `confidential` KB 必须显式 `allow_confidential=true`。
8. 前端静态文件由 FastAPI 从 `web/dist` 提供；没有构建产物时 API 仍可运行，根路径给出构建提示。
9. API 依赖作为可选 extra `[api]`，CLI 用户不需要安装 FastAPI。

## 备选方案

- **Celery / RQ + Redis**：适合多用户、可重试、可持久化，但 v2 是本地单用户，运维成本过高；排除。
- **请求内同步执行**：实现最简单，但几分钟的请求容易超时、断连，前端无法轮询；排除。
- **允许多作业并行**：会突破 DeepSeek 低余额并发上限；排除。
- **允许用户上传 KB**：需要额外的存储隔离、清理和信任边界；v2 排除。
- **v2 就加账号/权限**：本地工具没有这个需求，先保持 localhost-only；后续再按需要加 token/认证。

## 后果

- 吞吐量受单 worker 限制；这是有意的，优先避免模型并发失控。
- 服务重启时未完成作业会丢失；磁盘上的已完成结果仍可审计。
- 远程部署前必须补认证；当前安全边界依赖 `127.0.0.1` 绑定。
- 未来可把 worker 换成持久队列，而不改 HTTP 契约与前端。
