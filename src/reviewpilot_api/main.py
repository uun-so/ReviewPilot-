"""FastAPI application for ReviewPilot v2."""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from reviewpilot import __version__
from reviewpilot.config import AppConfig, load_config, stricter_sensitivity
from reviewpilot.ingest.manifest import ManifestError, load_manifest
from reviewpilot_api.jobs import Job, JobManager
from reviewpilot_api.registry import KbNotFound, KbRegistry
from reviewpilot_api.schemas import (
    CheckRequest,
    HealthOut,
    JobOut,
    KbIndexOut,
    KbOut,
    MAX_ARTICLE_CHARS,
)


def _job_out(job: Job) -> JobOut:
    succeeded = job.status == "succeeded"
    return JobOut(
        id=job.id,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        article_name=job.article_name,
        kb=job.kb_id,
        summary=job.summary,
        error=job.error,
        result_url=f"/api/jobs/{job.id}/result" if succeeded else None,
        report_url=f"/api/jobs/{job.id}/report" if succeeded else None,
    )


def _require_succeeded(manager: JobManager, job_id: str) -> Job:
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    if job.status != "succeeded" or job.run_dir is None:
        raise HTTPException(status_code=409, detail="作业尚未成功完成")
    return job


def create_app(
    *,
    kb_root: Path | None = None,
    runs_dir: Path | None = None,
    config: AppConfig | None = None,
    registry: KbRegistry | None = None,
    manager: JobManager | None = None,
    web_dist: Path | None = None,
) -> FastAPI:
    load_dotenv()
    config = config or load_config()
    kb_root = (kb_root or Path(os.environ.get("REVIEWPILOT_KB_ROOT", "kb"))).resolve()
    runs_dir = (runs_dir or Path(os.environ.get("REVIEWPILOT_RUNS_DIR", "runs"))).resolve()
    registry = registry or KbRegistry(kb_root)
    manager = manager or JobManager(runs_dir, config, registry)

    # The manager owns the effective config/registry/run directory; use those
    # so injected test instances and environment settings stay consistent.
    config = manager.config
    registry = manager.registry
    runs_dir = manager.runs_dir
    web_dist = (web_dist or Path(os.environ.get("REVIEWPILOT_WEB_DIST", "web/dist"))).resolve()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        manager.start()
        try:
            yield
        finally:
            manager.stop()

    app = FastAPI(title="ReviewPilot API", version=__version__, lifespan=lifespan)
    app.state.config = config
    app.state.registry = registry
    app.state.manager = manager

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthOut)
    def health() -> HealthOut:
        return HealthOut(
            version=__version__,
            api_key_configured=bool(os.environ.get("DEEPSEEK_API_KEY")),
            kb_root=str(registry.kb_root),
            runs_dir=str(runs_dir),
            concurrency=config.concurrency,
            models={
                "extraction": config.models.extraction,
                "judge": config.models.judge,
                "verifier": config.models.verifier,
            },
            max_article_chars=MAX_ARTICLE_CHARS,
        )

    @app.get("/api/kbs", response_model=list[KbOut])
    def list_kbs() -> list[KbOut]:
        return [
            KbOut.model_validate(info, from_attributes=True)
            for info in registry.list()
        ]

    @app.get("/api/kbs/{kb_id}", response_model=KbOut)
    def get_kb(kb_id: str) -> KbOut:
        try:
            info = registry.info(kb_id)
        except KbNotFound as exc:
            raise HTTPException(status_code=404, detail="知识库不存在") from exc
        return KbOut.model_validate(info, from_attributes=True)

    @app.post("/api/kbs/{kb_id}/index", response_model=KbIndexOut)
    async def index_kb(kb_id: str) -> KbIndexOut:
        try:
            stats = await asyncio.to_thread(registry.index, kb_id)
        except KbNotFound as exc:
            raise HTTPException(status_code=404, detail="知识库不存在") from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"索引失败：{exc}") from exc
        return KbIndexOut(
            id=kb_id,
            name=stats.manifest_name,
            version=stats.manifest_version,
            sensitivity=stats.sensitivity,
            documents=stats.documents,
            chunks=stats.chunks,
        )

    @app.post("/api/checks", response_model=JobOut, status_code=202)
    def create_check(request: CheckRequest) -> JobOut:
        try:
            kb_path = registry.resolve(request.kb)
        except KbNotFound as exc:
            raise HTTPException(status_code=404, detail="知识库不存在") from exc

        try:
            loaded = load_manifest(kb_path)
        except ManifestError as exc:
            raise HTTPException(status_code=400, detail=f"知识库无效：{exc}") from exc

        effective = stricter_sensitivity(
            config.sensitivity, loaded.manifest.sensitivity
        )
        if effective != "public" and not request.allow_confidential:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"知识库敏感级别为 {effective}，"
                    "必须显式 allow_confidential=true 才能发送到云端"
                ),
            )
        if not (kb_path / "index.sqlite").is_file():
            raise HTTPException(
                status_code=409,
                detail="知识库尚未建立索引，请先重建索引",
            )

        article_name = Path(request.article_name).name or "article.md"
        job = manager.submit(
            article_text=request.article_text,
            article_name=article_name,
            kb_id=request.kb,
            allow_confidential=request.allow_confidential,
        )
        return _job_out(job)

    @app.get("/api/jobs", response_model=list[JobOut])
    def list_jobs(
        limit: int = Query(default=20, ge=1, le=100),
    ) -> list[JobOut]:
        return [_job_out(job) for job in manager.list(limit=limit)]

    @app.get("/api/jobs/{job_id}", response_model=JobOut)
    def get_job(job_id: str) -> JobOut:
        job = manager.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="作业不存在")
        return _job_out(job)

    @app.get("/api/jobs/{job_id}/result")
    def get_result(job_id: str) -> JSONResponse:
        job = _require_succeeded(manager, job_id)
        assert job.run_dir is not None
        path = job.run_dir / "result.json"
        if not path.is_file():
            raise HTTPException(status_code=500, detail="结果文件缺失")
        try:
            return JSONResponse(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=500, detail=f"结果读取失败：{exc}") from exc

    @app.get("/api/jobs/{job_id}/report")
    def get_report(job_id: str) -> PlainTextResponse:
        job = _require_succeeded(manager, job_id)
        assert job.run_dir is not None
        path = job.run_dir / "report.md"
        if not path.is_file():
            raise HTTPException(status_code=500, detail="报告文件缺失")
        return PlainTextResponse(
            path.read_text(encoding="utf-8"),
            media_type="text/markdown; charset=utf-8",
        )

    index_file = web_dist / "index.html"
    if web_dist.is_dir() and index_file.is_file():

        @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
        def root_index() -> FileResponse:
            # The HTML entry point must always be revalidated; hashed assets
            # under /assets can still be cached normally. Without this, an old
            # index.html can keep loading a stale JS bundle after a deploy.
            return FileResponse(
                index_file,
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )

        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    else:

        @app.get("/", include_in_schema=False)
        def root() -> HTMLResponse:
            return HTMLResponse(
                "<!doctype html><html lang='zh-CN'><meta charset='utf-8'>"
                "<title>ReviewPilot API</title>"
                "<body style='font-family:system-ui;max-width:720px;margin:60px auto;line-height:1.6'>"
                "<h1>ReviewPilot API</h1>"
                "<p>前端尚未构建。运行 <code>npm --prefix web install &amp;&amp; "
                "npm --prefix web run build</code>，然后重启服务；或访问 "
                "<a href='/docs'>/docs</a> 查看 API。</p></body></html>"
            )

    return app


app = create_app()


def run() -> None:
    import uvicorn

    host = os.environ.get("REVIEWPILOT_HOST", "127.0.0.1")
    port = int(os.environ.get("REVIEWPILOT_PORT", "8000"))
    uvicorn.run("reviewpilot_api.main:app", host=host, port=port)


if __name__ == "__main__":
    run()
