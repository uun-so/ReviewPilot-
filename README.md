# ReviewPilot

> 输入一篇 AI 写的技术文章，输出逐句核验结论：每条可判定的主张，要么有知识库证据支撑，要么明确标成存疑。不替模型猜，也不让模型凭内部知识给结论。

**当前状态：v0.2.2。** CLI（`kb index` / `kb inspect` / `check` / `eval`）与 Web API / React + TypeScript 前端均可用：manifest 校验、Markdown/HTML/TXT 解析、结构感知切块、SQLite FTS5 + jieba 索引、主张抽取与逐字锚定、单跳证据判定、三道闸门、`result.json` / `report.md` / `trace.jsonl`。M3 的 60 条与 v0.1 的 200 条评测均通过；v2 的 FastAPI 后端与前端联调、wheel/sdist 打包与全新 venv 验证已完成。结果见下文与 [v0.1 评测记录](docs/eval/v0.1.0-2026-11-15.md)。

## 它保证什么

- 每条 支持 结论都必须附知识库中的**逐字引用**；引用必须能在源文档中定位，不能由模型改写。
- 每条 支持 或 冲突 结论都必须通过三道闸门：schema 校验、逐字引用校验、独立校验。任何一道失败，结论降级为「存疑」。
- 结论可复现：运行记录文章哈希、KB manifest 版本与哈希、模型配置、提示词版本和代码版本。
- 知识库之外的内容不会被模型内部知识补全；检索不到就输出「存疑」，而不是猜。

## 它不保证什么

- **不保证知识库本身正确。** 它保证的是「相对于这个 KB 的证据链完整」，不是绝对真理。
- **不执行代码。** 代码块不运行、不 lint、不判断能否编译；只核验自然语言中关于代码行为的主张。
- **v1 不做跨文档综合。** 需要两篇以上文档才能推出的主张，会标为「存疑」，原因写明 跨文档综合未启用 。
- **不是通用事实核查器。** 换知识库之前，覆盖范围就是那个知识库的范围。
- **不承诺云端数据不被用于训练。** 默认使用 DeepSeek API；其隐私政策允许用输入/输出改进模型，未提供零数据保留选项。公开内容默认放行，内部/机密语料必须显式覆盖（见 [ADR 0011](docs/adr/0011-privacy-provider-boundary.md)）。

## 工作流程

```text
article.md
   │
   ├─ 解析与切句（保留原文字符偏移）
   ├─ 主张抽取（LLM 只返回逐字片段）
   ├─ 锚点定位（程序做子串校验，失败即丢弃并记录）
   ├─ 检索（SQLite FTS5 + jieba BM25，结构感知切块，单跳）
   ├─ 判定（DeepSeek v4-pro，只看到检索到的 KB 片段）
   ├─ 三道闸门（schema / 逐字引用 / 独立校验）
   └─ report.md + result.json + trace.jsonl
```

核验单位是**原子主张**，不是句子：一句话含两个主张就拆开；相邻多句构成一个主张时，合并为一个**连续**的原文片段；不相邻的句子若需合并，拆成多个主张，避免伪造连续性。最终仍按原句分组展示。观点、预测、定义、修辞和代码内容单独放入 未核验 区，并注明不可核验的原因。

## 结论标签

| 标签 | 含义 | 证据要求 |
|---|---|---|
| **支持** | 知识库中有直接证据，单独看引用即可推出主张 | ≥1 条逐字引用；全部来自同一篇文档；三道闸门通过 |
| **存疑** | 无法达到「支持」；可能是无证据、证据不足、版本不匹配、需要跨文档综合或任一道闸门失败 | 无硬性要求；必须写明原因 |
| **与证据冲突** | 知识库中存在明确反证 | ≥1 条逐字反证；双方证据都列出；跨版本冲突单独标注，不自动选边 |
| **未核验** | 不是可判定主张：观点、预测、定义、修辞，以及锚定/抽取失败的可判定主张 | 不进入检索与判定；展示原因 |

标题和代码块是结构内容，直接跳过句子切分，不产生核验结论；未核验区只列出被判为不可判定的正文句子。「部分支持」归入「存疑」，并在原因中写清哪一部分被证据覆盖。判定细节见 [ADR 0002](docs/adr/0002-verdict-taxonomy.md) 与 [ADR 0004](docs/adr/0004-evidence-gates.md)。

## 技术栈

### v1（当前版本）

| 层 | 选型 | 说明 |
|---|---|---|
| 运行时 | Python 3.13 | 本机已验证 3.13.15 |
| CLI | Typer + Rich | `reviewpilot` 控制台入口 |
| 配置 | Pydantic v2 + PyYAML | `reviewpilot.yaml` |
| 检索 | SQLite FTS5 + jieba | 本地、确定性、无额外服务；trigram 对两字中文查询不可用，因此用 jieba 预分词 |
| 解析 | 自研 Markdown 块扫描器 + BeautifulSoup4 | Markdown 保留字符偏移；HTML 抽取规范化文本，原始文件保留审计 |
| 模型 | DeepSeek Responses API（openai SDK） | `deepseek-v4-pro` 判定/校验，`deepseek-flash` 抽取/检索式 |
| 测试 | pytest + respx | 单元测试不触网；respx mock HTTP |

### v2（0.2.2，已完成）

- FastAPI 后端 + React / TypeScript / Vite 前端，复用同一判定引擎。
- 单进程作业队列、KB 白名单、默认只监听 `127.0.0.1`。
- 按需引入本地 embedding / 向量库与 LangChain 仍未启用，保持 BM25 + 证据闸门不变。

## 快速开始

前置：Python 3.13、DeepSeek API Key。

```powershell
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
reviewpilot --help
pytest
```

```bash
# macOS / Linux / Git Bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
reviewpilot --help
pytest
```

### 安装方式

- 从仓库开发安装：`pip install -e ".[dev]"`
- 带 API 依赖：`pip install -e ".[dev,api]"`
- 从构建好的 wheel 安装：`pip install dist/reviewpilot-0.2.2-py3-none-any.whl`
- wheel + API：`pip install "dist/reviewpilot-0.2.2-py3-none-any.whl[api]"`

### v0.1 目标用法

```bash
# 1. 校验 manifest 并重建索引
reviewpilot kb index --kb kb/demo

# 2. 核验一篇文章
reviewpilot check article.md --kb kb/demo --out runs

# 3. 跑金标集
reviewpilot eval --gold eval/gold --kb kb/demo
```

### 打包与发布

```bash
pip install -e ".[dev]"   # dev 依赖包含 build
python -m build
# dist/reviewpilot-0.2.2-py3-none-any.whl
# dist/reviewpilot-0.2.2.tar.gz
```

全新 venv 验证 wheel：

```powershell
python -m venv .venv-m4
.venv-m4\Scripts\python -m pip install dist\reviewpilot-0.2.2-py3-none-any.whl
.venv-m4\Scripts\reviewpilot --version
.venv-m4\Scripts\reviewpilot --help
```

已在全新 venv 验证：0.2.2 wheel + `[api]` 安装后 `reviewpilot --version`、`reviewpilot-api`、`/api/health` 和静态首页可用；源码 `pip install -e ".[dev]"` 后 50 项 Python 测试通过；前端 `npm --prefix web run test` 的 1 项回归测试通过。真实 API 端到端也已跑通（提交 → 轮询 → result/report）。

`kb index` / `kb inspect` / `check` / `eval` 均可用。`eval` 在任一 `human_verdict` 为空时仍会以退出码 3 拒绝运行。

### 跑通仓库内示例

```bash
reviewpilot kb index --kb kb/demo
reviewpilot check examples/demo-article.md --kb kb/demo --out runs
```

`examples/demo-article.md` 故意包含四类内容：可被 KB 支持的主张、与 KB 明确冲突的主张、KB 未覆盖的主张、以及一条主观观点。运行后查看 `runs/<run_id>/report.md`；存在冲突时退出码为 2。

## Web API 与前端（v2，0.2.2）

v2 提供 FastAPI 后端和 React / TypeScript / Vite 前端，复用同一判定引擎；CLI 行为不变。

### 启动

```powershell
pip install -e ".[dev,api]"
npm --prefix web install
npm --prefix web run build
reviewpilot-api
# 打开 http://127.0.0.1:8000
```

开发模式：

```powershell
reviewpilot-api                 # 后端 :8000
npm --prefix web run dev        # 前端 :5173，/api 代理到 :8000
```

如果 `web/dist` 不存在，FastAPI 仍可运行，根路径会提示先构建前端；API 文档在 `/docs`。

### 工作方式

- 前端只上传文章文本；知识库从服务端 `kb/` 白名单中选择，不能传任意路径。
- 后端单进程作业队列，一次只跑一个核验；每个作业内部并发默认 4。
- API Key 只在服务端 `.env`，不会下发到浏览器。
- 作业完成后可查看逐条结论、证据和未核验内容，并下载 `result.json` / `report.md`。
- 作业状态保存在内存中，完成后结果落在 `runs/`；重启服务后历史作业列表会清空，但磁盘结果仍在。

### 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `REVIEWPILOT_KB_ROOT` | `kb` | 扫描子目录中的 manifest |
| `REVIEWPILOT_RUNS_DIR` | `runs` | 作业输入与结果目录 |
| `REVIEWPILOT_WEB_DIST` | `web/dist` | 构建后的前端 |
| `REVIEWPILOT_HOST` / `REVIEWPILOT_PORT` | `127.0.0.1` / `8000` | 监听地址 |
| `DEEPSEEK_API_KEY` | — | 服务端模型 Key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | 可选 API 地址 |

### API

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/health` | 版本、模型、Key 是否配置 |
| GET | `/api/kbs` | KB 列表、敏感级别、索引状态 |
| POST | `/api/kbs/{id}/index` | 重建 KB 索引 |
| POST | `/api/checks` | 提交核验（`article_text` / `article_name` / `kb` / `allow_confidential`） |
| GET | `/api/jobs/{id}` | 作业状态与摘要 |
| GET | `/api/jobs/{id}/result` | 完整 `result.json` |
| GET | `/api/jobs/{id}/report` | `report.md` |
| GET | `/docs` | OpenAPI 文档 |

### 安全边界

默认只监听 `127.0.0.1`，没有账号体系，**不要直接暴露到公网**。文章全文与检索片段会发送到 DeepSeek；`internal` / `confidential` KB 必须在前端显式勾选允许云端。作业输入副本始终保存在本地 `runs/`（API 暂未提供 `--no-store-article` 等价开关）。

## 知识库格式

```text
kb/<name>/
├── manifest.yaml          # 版本、来源、敏感级别
├── sources/               # Markdown / HTML / TXT 原文
│   ├── http-client.md
│   └── ...
└── index.sqlite           # 生成物；不提交到版本库
```

`manifest.yaml` 示例：

```yaml
name: python-http-demo
version: "2026.11"
effective_date: 2026-11-01
sensitivity: public          # public | internal | confidential
sources:
  - path: sources/http-client.md
    title: "http.client — HTTP protocol client"
    format: markdown          # markdown | html | text
    url: https://docs.python.org/3/library/http.client.html
    retrieved_at: 2026-11-14
    version: "3.13"           # 文档对应的软件/规范版本
    sha256: ""                 # 可选；填写后索引时校验
```

| 字段 | 必填 | 用途 |
|---|---|---|
| `name` / `version` | 是 | 运行记录与引用绑定；同一次运行只用一个版本 |
| `effective_date` | 是 | 时效判断与跨版本冲突标注 |
| `sensitivity` | 是 | `internal` / `confidential` 默认拒绝云端调用，需 `--allow-confidential` |
| `sources[].path` | 是 | 相对 KB 根目录的路径 |
| `sources[].version` | 建议 | 主张中出现版本号时用于匹配；缺失则相关主张更可能判为存疑 |
| `sources[].sha256` | 否 | 填写后索引时校验；不填则索引器计算并写入索引元数据 |

索引与 manifest 哈希绑定；重建索引是显式命令。引用中的字符偏移指向**规范化文本**（Markdown 原文或 HTML 抽取后的文本），不是原始 HTML 的 DOM 偏移。

## 配置

`reviewpilot.yaml`：

```yaml
kb: kb/demo
sensitivity: public
concurrency: 4

models:
  extraction: deepseek-flash
  query: deepseek-flash
  judge: deepseek-v4-pro
  verifier: deepseek-v4-pro
  judge_effort: none
  verifier_effort: low

report:
  annotated: true
```

环境变量：

| 变量 | 必填 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 是 | 只从环境读取，不写入 trace 或报告 |
| `DEEPSEEK_BASE_URL` | 否 | 默认 `https://api.deepseek.com`；代理场景才需要 |

有效敏感级别取 manifest 与配置中**更严格**的一方。`internal` / `confidential` 需要显式 `--allow-confidential` 才允许发送到云端。

## 输出

每次运行写入 `runs/<run_id>/`：

| 文件 | 用途 |
|---|---|
| `result.json` | 规范输出；CI、评测、二次处理都以它为准 |
| `report.md` | 人读报告；按原句分组，附证据与未核验区 |
| `trace.jsonl` | 每次模型调用的输入摘要、用量、耗时、闸门结果；不包含 API Key |
| `article.md` | 原文副本；`--no-store-article` 时只保留哈希与主张 |

`result.json` 结构（v1.0）：

```json
{
  "schema_version": "1.0",
  "run": {
    "run_id": "20261114T120000Z-a1b2c3d4",
    "created_at": "2026-11-14T12:00:00Z",
    "article": {"path": "article.md", "sha256": "…", "char_count": 5231},
    "kb": {"name": "python-http-demo", "version": "2026.11", "manifest_sha256": "…"},
    "models": {"judge": "deepseek-v4-pro", "verifier": "deepseek-v4-pro", "judge_effort": "none", "verifier_effort": "low"},
    "prompt_version": "2026-11-15.1",
    "code_version": "0.2.2"
  },
  "summary": {"claims_total": 42, "supported": 18, "conflict": 3, "uncertain": 21, "unverified": 7},
  "sentences": [
    {"sentence_id": "s1", "text": "…", "char_start": 0, "char_end": 42, "claim_ids": ["c1"]}
  ],
  "claims": [
    {
      "claim_id": "c1",
      "quote": "HTTPConnection 的默认超时是 30 秒",
      "char_start": 120,
      "char_end": 145,
      "sentence_ids": ["s1"],
      "verdict": "supported",
      "reason": "知识库文档明确写出默认值为 30 秒",
      "evidence": [
        {
          "doc_id": "doc-001",
          "doc_title": "http.client — HTTP protocol client",
          "source_path": "sources/http-client.md",
          "source_version": "3.13",
          "quote": "The default timeout is 30 seconds.",
          "char_start": 812,
          "char_end": 845,
          "relation": "supports",
          "used_for_verdict": true,
          "chunk_id": "sources/http-client.md#c0001"
        }
      ],
      "gates": {"schema": "pass", "quote": "pass", "entailment": "pass"},
      "usage": {"input_tokens": 3100, "output_tokens": 280}
    }
  ],
  "unverified": [
    {"sentence_id": "s9", "text": "我认为这是最好的方案。", "reason": "opinion"}
  ]
}
```

字段约定：

- `verdict`：`supported` / `conflict` / `uncertain`。
- `relation`：`supports` / `contradicts`。
- `used_for_verdict=false` 的证据仅用于展示（例如跨文档的支持线索），不参与判定。
- `chunk_id`：证据来源的检索块标识，便于在 `trace.jsonl` 与 KB 索引之间回溯。
- `unverified.reason`：`opinion` / `prediction` / `definition` / `rhetoric` / `code` / `other`。
- `gates`：`pass` / `fail`；任一 `fail` 时 `verdict` 必须是 `uncertain`。
- 字符偏移是 Python 字符串下标，指向规范化文本。

退出码：

| 码 | 含义 |
|---:|---|
| 0 | 无存疑、无冲突（全部支持或未核验） |
| 1 | 存在存疑 |
| 2 | 存在与证据冲突 |
| 3 | 运行错误（配置、解析、API、权限等） |
| 4 | 未抽取到任何可判定主张 |

## 评测

金标集是发布门槛，不是装饰。标注时**看不到系统结论**，只拿主张与知识库做独立判断。

| 阶段 | 规模 | 门槛 |
|---|---|---|
| M3 原型门槛 | 2 篇 AI 文章 / 约 60 条主张 | 假支持数 = 0；证据逐字有效率 = 100%；支持一致率 ≥95%；冲突召回 ≥80% |
| v0.1 发布门槛 | 5 篇 / 约 200 条主张 | 假支持数 = 0；支持一致率 ≥95%；冲突召回 ≥80% |

M3 的标注材料已生成：

- `eval/gold/labeling-sheet.md`：人读盲标表，不含任何系统结论。
- `eval/gold/<case>/labels.yaml`：需要填写 `human_verdict`（`supported` / `conflict` / `uncertain` / `non_claim`）。
- `eval/gold/README.md`：盲标约定与步骤。

标完后运行：

```bash
reviewpilot eval --gold eval/gold --kb kb/demo
```

评测 harness 会逐 case 跑完整流水线，按字符区间匹配金标与系统主张，输出 `eval/runs/<timestamp>/eval-report.md`。在全部 `human_verdict` 填完之前，`eval` 会拒绝运行；系统支持但金标未覆盖的主张会计入 `ungraded_support` 并使门槛失败。指标定义与标注流程见 [ADR 0010](docs/adr/0010-evaluation-gate.md)。

### M3 评测结果

| 指标 | 结果 |
|---|---:|
| 金标 / 系统主张 | 60 / 58 |
| 匹配 | 58（2 条观点句未生成主张，符合预期） |
| 假支持 | **0** |
| 未匹配支持 | 0 |
| 支持一致率 | **100.0%**（43/43） |
| 冲突召回 | **100.0%**（11/11） |
| 覆盖率 | 100.0% |
| 证据逐字有效 | 100.0%（58/58） |
| 门槛 | **通过** |

完整报告：[docs/eval/m3-2026-11-15.md](docs/eval/m3-2026-11-15.md) · [JSON](docs/eval/m3-2026-11-15.json)

首轮评测有两条支持结论被保守地判为「存疑」（`http-article-007` 省略可选参数 `encode_chunked`；`json-article-011` 的参数默认值 vs 有效默认分隔符）。已通过抽取/校验提示词修复：省略可选参数和更简略的签名不构成冲突，参数默认值与有效默认行为分开判断。修复后复跑无分歧。

### v0.1 金标扩充

- 6 个 case / **200 条**主张，全部完成人工盲标；demo KB 为 `2026.11.1`（6 篇文档）。
- 新增主题：`pathlib`、`datetime`、`logging`、`argparse`。

| 指标 | 结果 |
|---|---:|
| 金标 / 系统主张 | 200 / 190 |
| 匹配 | 190 |
| 假支持 | **0** |
| 未匹配支持 | 0 |
| 支持一致率 | **99.1%**（114/115） |
| 冲突召回 | **98.0%**（49/50） |
| 覆盖率 | 100.0% |
| 证据逐字有效 | 100.0%（180/180） |
| 门槛 | **通过** |

完整报告：[docs/eval/v0.1.0-2026-11-15.md](docs/eval/v0.1.0-2026-11-15.md) · [JSON](docs/eval/v0.1.0-2026-11-15.json)

剩余两处分歧均为保守的「存疑」，没有假支持：`argparse-article-017`（`-h/--help` 默认自动添加；verifier 没有把签名里的 `add_help=True` 默认值连起来）与 `logging-article-020`（`basicConfig()` 默认级别；KB 只写了根 logger 默认 `WARNING`）。另有 1 条被抽取切碎的子句（`datetime.utcnow()` 的弃用说明）未匹配金标，属于抽取粒度问题。

## 模型与成本

| 角色         | 模型                | 思考模式   | 说明                          |
| ---------- | ----------------- | ------ | --------------------------- |
| 主张抽取 / 检索式 | `deepseek-flash`  | `none` | 快、便宜；只输出原文片段与关键词            |
| 判定         | `deepseek-v4-pro` | `none` | temperature=0；只看到检索到的 KB 片段 |
| 独立校验       | `deepseek-v4-pro` | `low`  | 只看到主张与引用片段；与判定不一致即存疑        |


按 2,000 词、约 80 条主张、每条 6 个证据块估算，默认配置约 **$0.4–0.5/篇**（非高峰），高峰约翻倍。仓库内 8 条主张的 demo 真实运行消耗约 11k input / 2k output tokens，按非高峰价、全部按 Pro 上限计算约 **$0.01**。没有 Batch API；目录批处理靠并发（默认 4；低余额账户的并发上限可能只有 5，充值后可调高；官方账户上限 Flash 2500 / Pro 500）。高峰为 UTC 周一至周五 01:00–04:00、06:00–10:00（北京时间工作日 09:00–12:00、14:00–18:00），其余时间半价。

模型 ID 可能被供应商静默更新；运行元数据会记录供应商返回的模型标识，模型更新后需要重跑评测。详见 [ADR 0007](docs/adr/0007-deepseek-api-model-tiering.md)。

## 局限

- **闭世界**：KB 未覆盖的真实主张也会标「存疑」；这是设计选择，不是 bug。
- **单跳**：跨文档综合在 v1 中不启用。
- **结构内容不核验**：标题和代码块不进入句子切分；只核验正文、列表和表格中的自然语言主张。
- **模型输出围栏**：模型偶尔会在 `json_schema` 模式下仍包一层 Markdown 代码围栏。provider 会在解析前剥离围栏，但随后仍走严格 schema 与证据闸门，不放宽结论。
- **HTML 偏移**：引用指向抽取后的规范化文本，不是原始 DOM。
- **中文分词**：jieba 可能切碎英文标识符；检索式抽取会保留 API 名、版本号、数字的原样形式。
- **金标规模**：200 条金标的统计置信度仍有限；更大规模（尤其是真实文章）需后续扩充。
- **数据使用**：DeepSeek API 可能将输入用于训练；机密语料需显式覆盖或改用未来的本地 provider。

## 路线图

| 版本 | 内容 |
|---|---|
| v0.1.0 | 200 条门槛通过；wheel/sdist 已发布 |
| v0.2.2 | FastAPI 后端 + React / TypeScript 前端已完成；可选 embedding/向量库与 LangChain 仍按需引入 |
| 后续 | PDF/DOCX、HTML 文档站抓取、多跳综合、CI 门禁模式、英文报告 |

## 架构决策记录（ADR）

| 编号 | 决策 |
|---|---|
| [0001](docs/adr/0001-closed-world-kb.md) | 闭世界知识库与证据门控 |
| [0002](docs/adr/0002-verdict-taxonomy.md) | 三标签结论与未核验区 |
| [0003](docs/adr/0003-atomic-claims-anchors.md) | 原子主张与逐字锚点 |
| [0004](docs/adr/0004-evidence-gates.md) | 严格证据闸门与独立校验 |
| [0005](docs/adr/0005-single-hop-mvp.md) | 单跳 MVP 与多跳延后 |
| [0006](docs/adr/0006-retrieval-chunking.md) | FTS5 + jieba + 结构感知切块 |
| [0007](docs/adr/0007-deepseek-api-model-tiering.md) | DeepSeek Responses API 与模型分工 |
| [0008](docs/adr/0008-fail-closed-idempotency.md) | 失败降级与幂等运行 |
| [0009](docs/adr/0009-kb-manifest-version-conflict.md) | KB manifest、版本与冲突策略 |
| [0010](docs/adr/0010-evaluation-gate.md) | 评测门槛：假支持数 = 0 |
| [0011](docs/adr/0011-privacy-provider-boundary.md) | 隐私边界与 provider 抽象 |
| [0012](docs/adr/0012-output-contract.md) | 输出契约与退出码 |
| [0013](docs/adr/0013-web-api-job-model.md) | Web API 边界与单进程作业模型 |
| [0014](docs/adr/0014-frontend-contract.md) | 前端技术栈与结果展示契约 |

## 开发

```text
ReviewPilot/
├── src/reviewpilot/       # 判定引擎与 CLI
├── src/reviewpilot_api/   # FastAPI 后端、作业队列、KB registry
├── web/                   # React + TypeScript + Vite 前端
├── tests/                 # pytest，默认不触网
├── docs/adr/              # 14 篇架构决策记录
├── docs/eval/             # 归档的评测报告
├── eval/gold/             # 200 条人工盲标金标
├── examples/              # 可复现的 demo 文章
├── scripts/               # 盲标与标注表生成脚本
├── kb/demo/               # 示例知识库
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

```text
src/reviewpilot/
├── cli.py           # Typer 入口
├── config.py        # Pydantic 配置模型与加载
├── eval.py          # M3 金标评测 harness
├── pipeline.py      # 端到端核验流水线
├── domain.py        # result.json 领域模型
├── llm/             # DeepSeek Responses API 适配器
├── ingest/          # Markdown/HTML/TXT 解析与 manifest
├── index/           # 切块、FTS5 索引与 BM25 检索
├── claims/          # 句子切分、主张抽取与逐字锚定
├── retrieve/        # 查询构造（预留）
├── judge/           # 判定、独立校验、三道闸门
└── report/          # result.json / report.md / trace

src/reviewpilot_api/
├── main.py          # FastAPI 应用与路由
├── jobs.py          # 单进程作业队列
├── registry.py      # KB 白名单扫描与索引
└── schemas.py       # HTTP 请求/响应模型

web/
├── src/             # React 页面、API 客户端与样式
├── dist/            # 构建产物（由 FastAPI 托管；不提交）
└── package.json
```

## 九、其他文档
## 📚 项目完整文档
- [产品需求文档（PRD）](./docs/PRD.md)
- [竞品分析手册](./docs/competitor-analysis.md)