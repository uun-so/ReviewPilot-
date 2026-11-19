import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { CheckResult, Health, Job, KbInfo, Summary } from "./api";

vi.mock("./api", () => ({
  api: {
    health: vi.fn(),
    kbs: vi.fn(),
    indexKb: vi.fn(),
    createCheck: vi.fn(),
    getJob: vi.fn(),
    getResult: vi.fn(),
    resultUrl: (id: string) => `/api/jobs/${id}/result`,
    reportUrl: (id: string) => `/api/jobs/${id}/report`,
  },
}));

import { api } from "./api";
import App from "./App";

const health: Health = {
  status: "ok",
  version: "0.2.2",
  api_key_configured: true,
  kb_root: "kb",
  runs_dir: "runs",
  concurrency: 4,
  models: {
    extraction: "deepseek-flash",
    judge: "deepseek-v4-pro",
    verifier: "deepseek-v4-pro",
  },
  max_article_chars: 200_000,
};

const kbs: KbInfo[] = [
  {
    id: "demo",
    name: "python-stdlib-demo",
    version: "2026.11.1",
    sensitivity: "public",
    indexed: true,
    documents: 6,
    chunks: 6,
    error: null,
  },
];

const summary: Summary = {
  claims_total: 1,
  supported: 1,
  conflict: 0,
  uncertain: 0,
  unverified: 0,
};

const result: CheckResult = {
  schema_version: "1.0",
  run: {
    run_id: "r1",
    created_at: "2026-11-19T00:00:00+00:00",
    article: { path: "article.md", sha256: "x", char_count: 6 },
    kb: {
      name: "python-stdlib-demo",
      version: "2026.11.1",
      manifest_sha256: "x",
    },
    models: {
      judge: "deepseek-v4-pro",
      verifier: "deepseek-v4-pro",
      judge_effort: "none",
      verifier_effort: "low",
    },
    prompt_version: "p",
    code_version: "0.2.2",
  },
  summary,
  sentences: [
    {
      sentence_id: "s1",
      text: "示例主张。",
      char_start: 0,
      char_end: 5,
      block_kind: "paragraph",
      heading_path: "",
      claim_ids: ["c1"],
    },
  ],
  claims: [
    {
      claim_id: "c1",
      quote: "示例主张。",
      char_start: 0,
      char_end: 5,
      sentence_ids: ["s1"],
      verdict: "supported",
      reason: "文档支持",
      evidence: [],
      gates: { schema: "pass", quote: "pass", entailment: "pass" },
      usage: {},
    },
  ],
  unverified: [],
};

const baseJob = {
  id: "j1",
  created_at: "2026-11-19T00:00:00+00:00",
  started_at: null,
  finished_at: null,
  article_name: "article.md",
  kb: "demo",
  summary: null,
  error: null,
  result_url: null,
  report_url: null,
};

const queued: Job = { ...baseJob, status: "queued" };
const running: Job = {
  ...baseJob,
  status: "running",
  started_at: "2026-11-19T00:00:01+00:00",
};
const succeeded: Job = {
  ...baseJob,
  status: "succeeded",
  started_at: "2026-11-19T00:00:01+00:00",
  finished_at: "2026-11-19T00:00:02+00:00",
  summary,
  result_url: "/api/jobs/j1/result",
  report_url: "/api/jobs/j1/report",
};

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.health).mockResolvedValue(health);
    vi.mocked(api.kbs).mockResolvedValue(kbs);
    vi.mocked(api.createCheck).mockResolvedValue(queued);
    vi.mocked(api.getJob)
      .mockResolvedValueOnce(running)
      .mockResolvedValue(succeeded);
    vi.mocked(api.getResult).mockResolvedValue(result);
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the result after a succeeded job instead of staying on loading", async () => {
    render(<App />);

    expect(await screen.findByText(/已索引/)).toBeTruthy();

    fireEvent.change(screen.getByPlaceholderText(/粘贴一篇/), {
      target: { value: "示例主张。" },
    });
    fireEvent.click(screen.getByRole("button", { name: "开始核验" }));

    await waitFor(() => expect(api.createCheck).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByText("逐条结论")).toBeTruthy(), {
      timeout: 5_000,
    });

    expect(screen.getAllByText("支持").length).toBeGreaterThan(0);
    expect(screen.getAllByText("示例主张。").length).toBeGreaterThan(0);
    expect(screen.queryByText(/正在加载结果/)).toBeNull();
  });
});
