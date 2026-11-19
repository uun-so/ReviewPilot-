import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { api } from "./api";
import type {
  CheckResult,
  Claim,
  Health,
  Job,
  KbInfo,
  Sentence,
  Summary,
  Unverified,
  Verdict,
} from "./api";

declare const __APP_VERSION__: string;

const appVersion =
  typeof __APP_VERSION__ === "string" ? __APP_VERSION__ : "dev";

const VERDICT_META: Record<Verdict, { label: string; className: string }> = {
  supported: { label: "支持", className: "badge ok" },
  conflict: { label: "与证据冲突", className: "badge bad" },
  uncertain: { label: "存疑", className: "badge warn" },
};

const REASON_LABELS: Record<string, string> = {
  opinion: "观点",
  prediction: "预测",
  definition: "定义",
  rhetoric: "修辞",
  code: "代码",
  other: "其他不可判定",
  anchor_failed: "原文锚定失败",
  extraction_failed: "抽取失败",
};

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function formatTime(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN");
}

function SummaryCards({ summary }: { summary: Summary }) {
  return (
    <div className="summary-grid">
      <div className="stat total">
        <strong>{summary.claims_total}</strong>
        <span>可判定主张</span>
      </div>
      <div className="stat ok">
        <strong>{summary.supported}</strong>
        <span>支持</span>
      </div>
      <div className="stat bad">
        <strong>{summary.conflict}</strong>
        <span>冲突</span>
      </div>
      <div className="stat warn">
        <strong>{summary.uncertain}</strong>
        <span>存疑</span>
      </div>
      <div className="stat muted">
        <strong>{summary.unverified}</strong>
        <span>未核验</span>
      </div>
    </div>
  );
}

function ClaimCard({ claim, context }: { claim: Claim; context?: string }) {
  const meta = VERDICT_META[claim.verdict];
  return (
    <article className={`claim-card ${claim.verdict}`}>
      <div className="claim-head">
        <span className={meta.className}>{meta.label}</span>
        <span className="claim-id">{claim.claim_id}</span>
      </div>
      <blockquote className="claim-quote">{claim.quote}</blockquote>
      {context && context !== claim.quote && (
        <p className="sentence-context">原句：{context}</p>
      )}
      <p className="claim-reason">{claim.reason}</p>

      {claim.evidence.length > 0 && (
        <div className="evidence-list">
          {claim.evidence.map((evidence, index) => (
            <div
              className={`evidence ${evidence.relation}`}
              key={`${evidence.chunk_id}-${index}`}
            >
              <div className="evidence-head">
                <span className={`tag ${evidence.relation}`}>
                  {evidence.relation === "supports" ? "支持" : "反证"}
                </span>
                <strong>{evidence.doc_title}</strong>
                {evidence.source_version && (
                  <span className="version">v{evidence.source_version}</span>
                )}
                {!evidence.used_for_verdict && (
                  <span className="display-only">仅展示</span>
                )}
              </div>
              <blockquote>{evidence.quote}</blockquote>
            </div>
          ))}
        </div>
      )}

      <div className="gate-row">
        {Object.entries(claim.gates).map(([gate, result]) => (
          <span key={gate} className={`gate ${result}`}>
            {gate}: {result}
          </span>
        ))}
      </div>
    </article>
  );
}

function UnverifiedTable({ items }: { items: Unverified[] }) {
  if (items.length === 0) {
    return <p className="muted">没有未核验内容。</p>;
  }
  return (
    <div className="table-wrap">
      <table className="unverified-table">
        <thead>
          <tr>
            <th>句子</th>
            <th>原因</th>
            <th>原文</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.sentence_id}-${item.reason}`}>
              <td className="mono">{item.sentence_id}</td>
              <td>{REASON_LABELS[item.reason] ?? item.reason}</td>
              <td>{item.text}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [kbs, setKbs] = useState<KbInfo[]>([]);
  const [kbId, setKbId] = useState("");
  const [article, setArticle] = useState("");
  const [articleName, setArticleName] = useState("article.md");
  const [allowConfidential, setAllowConfidential] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingKbs, setLoadingKbs] = useState(false);
  const [resultAttempt, setResultAttempt] = useState(0);

  const selectedKb = kbs.find((kb) => kb.id === kbId);
  const maxChars = health?.max_article_chars ?? 200_000;
  const tooLong = article.length > maxChars;

  async function refresh() {
    setLoadingKbs(true);
    try {
      const [nextHealth, nextKbs] = await Promise.all([api.health(), api.kbs()]);
      setHealth(nextHealth);
      setKbs(nextKbs);
      setKbId((current) => {
        if (current && nextKbs.some((kb) => kb.id === current)) return current;
        return (
          nextKbs.find((kb) => kb.indexed)?.id ??
          nextKbs[0]?.id ??
          ""
        );
      });
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setLoadingKbs(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    if (!job || job.status === "succeeded" || job.status === "failed") {
      return;
    }
    const jobId = job.id;
    let cancelled = false;

    const tick = async () => {
      try {
        const next = await api.getJob(jobId);
        if (!cancelled) setJob(next);
      } catch (cause) {
        if (!cancelled) setError(errorText(cause));
      }
    };

    const timer = window.setInterval(tick, 1500);
    void tick();
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [job?.id, job?.status]);

  // Fetch the result in a separate effect. Fetching it inside the polling
  // effect races with the status update: setJob("succeeded") triggers this
  // effect's cleanup before the result request resolves, and the old
  // `cancelled` guard would drop the result forever.
  useEffect(() => {
    if (!job || job.status !== "succeeded" || result) {
      return;
    }
    const jobId = job.id;
    let cancelled = false;
    api
      .getResult(jobId)
      .then((loaded) => {
        if (!cancelled) setResult(loaded);
      })
      .catch((cause) => {
        if (!cancelled) setError(errorText(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [job?.id, job?.status, result, resultAttempt]);

  const sentenceById = useMemo(() => {
    const map = new Map<string, Sentence>();
    for (const sentence of result?.sentences ?? []) {
      map.set(sentence.sentence_id, sentence);
    }
    return map;
  }, [result]);

  const sortedClaims = useMemo(() => {
    return result
      ? [...result.claims].sort((left, right) => left.char_start - right.char_start)
      : [];
  }, [result]);

  const canRun =
    Boolean(article.trim()) &&
    Boolean(selectedKb?.indexed) &&
    !tooLong &&
    !busy &&
    health?.api_key_configured !== false;

  async function submit() {
    if (!selectedKb || !article.trim()) return;
    setBusy(true);
    setError("");
    setResult(null);
    setJob(null);
    setResultAttempt(0);
    try {
      const created = await api.createCheck({
        article_text: article,
        article_name: articleName,
        kb: selectedKb.id,
        allow_confidential: allowConfidential,
      });
      setJob(created);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setBusy(false);
    }
  }

  async function rebuildIndex() {
    if (!selectedKb) return;
    setLoadingKbs(true);
    setError("");
    try {
      await api.indexKb(selectedKb.id);
      await refresh();
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setLoadingKbs(false);
    }
  }

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      setArticle(text);
      setArticleName(file.name);
      setResult(null);
      setJob(null);
      setResultAttempt(0);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      event.target.value = "";
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">RP</span>
          <div>
            <h1>ReviewPilot</h1>
            <p>证据门控的技术文章核验</p>
          </div>
        </div>
        <div className="topbar-right">
          <a href="/docs" target="_blank" rel="noreferrer">
            API
          </a>
          <span
            className={`status-dot ${
              health?.api_key_configured ? "ok" : "warn"
            }`}
          />
          <span className="muted">
            {health ? `${health.models.judge} · v${health.version}` : "连接中"}
          </span>
        </div>
      </header>

      {error && (
        <div className="alert bad" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError("")} aria-label="关闭">
            ×
          </button>
        </div>
      )}

      <main className="layout">
        <section className="panel input-panel">
          <div className="panel-title">
            <h2>输入</h2>
            <span className="muted">Markdown / TXT</span>
          </div>

          <label className="field-label" htmlFor="kb">
            知识库
          </label>
          <select
            id="kb"
            value={kbId}
            onChange={(event) => {
              setKbId(event.target.value);
              setAllowConfidential(false);
            }}
            disabled={loadingKbs || kbs.length === 0}
          >
            {kbs.length === 0 && <option value="">暂无知识库</option>}
            {kbs.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name} · {kb.version}（{kb.sensitivity}）
              </option>
            ))}
          </select>

          {selectedKb && (
            <div className="kb-status">
              <span className={`dot ${selectedKb.indexed ? "ok" : "warn"}`} />
              {selectedKb.indexed ? (
                <span>
                  已索引 · {selectedKb.documents ?? "?"} 篇文档 /{" "}
                  {selectedKb.chunks ?? "?"} 个块
                </span>
              ) : (
                <span>尚未建立索引</span>
              )}
              {!selectedKb.indexed && (
                <button
                  type="button"
                  className="ghost small"
                  onClick={rebuildIndex}
                  disabled={loadingKbs}
                >
                  重建索引
                </button>
              )}
            </div>
          )}
          {selectedKb?.error && (
            <p className="inline-error">{selectedKb.error}</p>
          )}

          <div className="field-row">
            <label className="file-button">
              选择文件
              <input
                type="file"
                accept=".md,.markdown,.txt,text/plain,text/markdown"
                onChange={onFile}
              />
            </label>
            <span className={`counter ${tooLong ? "bad" : ""}`}>
              {article.length.toLocaleString()} / {maxChars.toLocaleString()}
            </span>
          </div>

          <textarea
            value={article}
            onChange={(event) => setArticle(event.target.value)}
            placeholder="粘贴一篇 AI 生成的技术文章……"
            spellCheck={false}
          />
          <p className="hint">
            文件名：{articleName}。标题和代码块不会进入核验，正文、列表和表格会。
          </p>

          <div className="notice">
            <strong>数据边界</strong>
            <span>
              文章全文与检索到的 KB 片段会发送到 DeepSeek；API Key
              只在服务端，不会下发到浏览器。
            </span>
          </div>

          {selectedKb && selectedKb.sensitivity !== "public" && (
            <label className="checkbox">
              <input
                type="checkbox"
                checked={allowConfidential}
                onChange={(event) => setAllowConfidential(event.target.checked)}
              />
              我确认允许将该 {selectedKb.sensitivity} 知识库的内容发送到云端
            </label>
          )}

          {health && !health.api_key_configured && (
            <div className="alert warn">
              服务端未配置 DEEPSEEK_API_KEY，无法发起核验。
            </div>
          )}

          <button
            type="button"
            className="primary"
            onClick={submit}
            disabled={!canRun}
          >
            {busy ? "提交中…" : "开始核验"}
          </button>
        </section>

        <section className="panel result-panel">
          <div className="panel-title">
            <h2>结果</h2>
            {result && job && (
              <div className="downloads">
                <a
                  href={api.resultUrl(job.id)}
                  target="_blank"
                  rel="noreferrer"
                >
                  result.json
                </a>
                <a href={api.reportUrl(job.id)} target="_blank" rel="noreferrer">
                  report.md
                </a>
              </div>
            )}
          </div>

          {!job && !result && (
            <div className="empty">
              <div className="empty-icon">◎</div>
              <h3>从一篇文章开始</h3>
              <p>选择知识库、粘贴文章，然后发起核验。</p>
              <ol>
                <li>每条可判定主张要么有 KB 逐字证据，要么标为存疑。</li>
                <li>支持/冲突结论都会经过逐字引用与独立校验。</li>
                <li>知识库没覆盖的内容不会被模型凭记忆补全。</li>
              </ol>
            </div>
          )}

          {job && (job.status === "queued" || job.status === "running") && (
            <div className="status-card">
              <div className="spinner" />
              <div>
                <strong>
                  {job.status === "queued" ? "排队中" : "正在核验"}
                </strong>
                <p className="muted">
                  {job.article_name} · KB：{job.kb}
                </p>
                <p className="muted small">
                  逐条主张检索、判定和独立校验，通常需要 1–5 分钟。
                </p>
              </div>
            </div>
          )}

          {job?.status === "failed" && (
            <div className="alert bad">
              <strong>核验失败</strong>
              <p>{job.error ?? "未知错误"}</p>
            </div>
          )}

          {job?.status === "succeeded" && !result && (
            <div className="status-card">
              <div className="spinner" />
              <div>
                <strong>正在加载结果…</strong>
                <p className="muted small">如果长时间没有响应，可以重试。</p>
              </div>
              <button
                type="button"
                className="ghost small retry-result"
                onClick={() => setResultAttempt((value) => value + 1)}
              >
                重试
              </button>
            </div>
          )}

          {result && (
            <div className="result-body">
              <SummaryCards summary={result.summary} />

              <div className="run-line">
                <span>
                  KB：{result.run.kb.name} `{result.run.kb.version}`
                </span>
                <span>文章：{result.run.article.path}</span>
                <span>完成：{formatTime(result.run.created_at)}</span>
              </div>

              <div className="section-head">
                <h3>逐条结论</h3>
                <span className="muted">{sortedClaims.length} 条</span>
              </div>
              {sortedClaims.length === 0 ? (
                <p className="muted">未抽取到可判定主张。</p>
              ) : (
                <div className="claim-list">
                  {sortedClaims.map((claim) => {
                    const context = claim.sentence_ids
                      .map((id) => sentenceById.get(id)?.text)
                      .find((text) => Boolean(text));
                    return (
                      <ClaimCard
                        key={claim.claim_id}
                        claim={claim}
                        context={context}
                      />
                    );
                  })}
                </div>
              )}

              <div className="section-head">
                <h3>未核验</h3>
                <span className="muted">{result.unverified.length} 条</span>
              </div>
              <UnverifiedTable items={result.unverified} />

              <details className="meta">
                <summary>运行元数据</summary>
                <dl>
                  <div>
                    <dt>run_id</dt>
                    <dd className="mono">{result.run.run_id}</dd>
                  </div>
                  <div>
                    <dt>文章 SHA-256</dt>
                    <dd className="mono">{result.run.article.sha256}</dd>
                  </div>
                  <div>
                    <dt>KB manifest</dt>
                    <dd className="mono">
                      {result.run.kb.manifest_sha256}
                    </dd>
                  </div>
                  <div>
                    <dt>模型</dt>
                    <dd>
                      判定 {result.run.models.judge} / 校验{" "}
                      {result.run.models.verifier}
                    </dd>
                  </div>
                  <div>
                    <dt>prompt / code</dt>
                    <dd className="mono">
                      {result.run.prompt_version} / {result.run.code_version}
                    </dd>
                  </div>
                </dl>
              </details>
            </div>
          )}
        </section>
      </main>

      <footer className="footer">
        <span>ReviewPilot</span>
        <span className="muted">
          本地优先 · 闭世界知识库 · 失败一律降级存疑
        </span>
        <span className="muted">Web v{appVersion}</span>
      </footer>
    </div>
  );
}
