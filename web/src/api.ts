export type Verdict = "supported" | "conflict" | "uncertain";
export type Relation = "supports" | "contradicts";

export interface Evidence {
  doc_id: string;
  doc_title: string;
  source_path: string;
  source_version: string | null;
  quote: string;
  char_start: number;
  char_end: number;
  relation: Relation;
  used_for_verdict: boolean;
  chunk_id: string;
}

export interface Claim {
  claim_id: string;
  quote: string;
  char_start: number;
  char_end: number;
  sentence_ids: string[];
  verdict: Verdict;
  reason: string;
  evidence: Evidence[];
  gates: Record<string, string>;
  usage: Record<string, number>;
}

export interface Sentence {
  sentence_id: string;
  text: string;
  char_start: number;
  char_end: number;
  block_kind: string;
  heading_path: string;
  claim_ids: string[];
}

export interface Unverified {
  sentence_id: string;
  text: string;
  reason: string;
}

export interface Summary {
  claims_total: number;
  supported: number;
  conflict: number;
  uncertain: number;
  unverified: number;
}

export interface CheckResult {
  schema_version: string;
  run: {
    run_id: string;
    created_at: string;
    article: { path: string; sha256: string; char_count: number };
    kb: { name: string; version: string; manifest_sha256: string };
    models: {
      judge: string;
      verifier: string;
      judge_effort: string;
      verifier_effort: string;
    };
    prompt_version: string;
    code_version: string;
  };
  summary: Summary;
  sentences: Sentence[];
  claims: Claim[];
  unverified: Unverified[];
}

export interface KbInfo {
  id: string;
  name: string;
  version: string;
  sensitivity: string;
  indexed: boolean;
  documents: number | null;
  chunks: number | null;
  error: string | null;
}

export interface Job {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  article_name: string;
  kb: string;
  summary: Summary | null;
  error: string | null;
  result_url: string | null;
  report_url: string | null;
}

export interface Health {
  status: string;
  version: string;
  api_key_configured: boolean;
  kb_root: string;
  runs_dir: string;
  concurrency: number;
  models: Record<string, string>;
  max_article_chars: number;
}

export interface CheckPayload {
  article_text: string;
  article_name: string;
  kb: string;
  allow_confidential: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (body && body.detail !== undefined) {
        detail = String(body.detail);
      }
    } catch {
      // keep the status text
    }
    throw new Error(detail || `请求失败（HTTP ${response.status}）`);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<Health>("/api/health"),
  kbs: () => request<KbInfo[]>("/api/kbs"),
  indexKb: (id: string) =>
    request<{ id: string; documents: number; chunks: number }>(
      `/api/kbs/${encodeURIComponent(id)}/index`,
      { method: "POST" },
    ),
  createCheck: (payload: CheckPayload) =>
    request<Job>("/api/checks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  getJob: (id: string) =>
    request<Job>(`/api/jobs/${encodeURIComponent(id)}`),
  getResult: (id: string) =>
    request<CheckResult>(`/api/jobs/${encodeURIComponent(id)}/result`),
  resultUrl: (id: string) => `/api/jobs/${encodeURIComponent(id)}/result`,
  reportUrl: (id: string) => `/api/jobs/${encodeURIComponent(id)}/report`,
};
