from __future__ import annotations

import shutil
import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from reviewpilot.config import AppConfig
from reviewpilot.index.fts import build_index
from reviewpilot_api.jobs import JobManager
from reviewpilot_api.main import create_app
from reviewpilot_api.registry import KbRegistry
from tests.fakes import FakeProvider
from tests.test_pipeline import _handler


def _kb_root(
    tmp_path: Path,
    kb_dir: Path,
    *,
    index: bool = True,
    sensitivity: str | None = None,
) -> Path:
    root = tmp_path / f"kbs-{uuid.uuid4().hex[:6]}"
    target = root / "demo"
    target.mkdir(parents=True)
    shutil.copytree(kb_dir, target, dirs_exist_ok=True)
    if sensitivity is not None:
        manifest = target / "manifest.yaml"
        text = manifest.read_text(encoding="utf-8").replace(
            "sensitivity: public", f"sensitivity: {sensitivity}"
        )
        manifest.write_text(text, encoding="utf-8")
    if index:
        build_index(target)
    return root


def _client(
    tmp_path: Path,
    root: Path,
    *,
    config: AppConfig | None = None,
    web_dist: Path | None = None,
):
    registry = KbRegistry(root)
    manager = JobManager(
        tmp_path / "runs",
        config or AppConfig(kb=root / "demo", concurrency=1),
        registry,
        provider_factory=lambda: FakeProvider(_handler),
    )
    app = create_app(
        registry=registry,
        manager=manager,
        web_dist=web_dist or tmp_path / "no-web",
    )
    return TestClient(app)


@pytest.fixture
def api_client(kb_dir: Path, tmp_path: Path):
    root = _kb_root(tmp_path, kb_dir)
    with _client(tmp_path, root) as client:
        yield client


def _wait(client: TestClient, job_id: str) -> dict:
    for _ in range(200):
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"succeeded", "failed"}:
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_health_and_kbs(api_client: TestClient) -> None:
    health = api_client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["version"] == "0.2.2"
    assert body["concurrency"] == 1
    assert body["max_article_chars"] == 200_000

    kbs = api_client.get("/api/kbs")
    assert kbs.status_code == 200
    data = kbs.json()
    assert len(data) == 1
    assert data[0]["id"] == "demo"
    assert data[0]["indexed"] is True
    assert data[0]["documents"] == 2


def test_check_flow(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/checks",
        json={
            "article_text": "HTTPConnection 默认超时为 30 秒。\n",
            "article_name": "article.md",
            "kb": "demo",
        },
    )
    assert response.status_code == 202, response.text
    job = response.json()
    assert job["status"] == "queued"

    finished = _wait(api_client, job["id"])
    assert finished["status"] == "succeeded", finished
    assert finished["summary"]["supported"] == 1
    assert finished["summary"]["claims_total"] == 1

    result = api_client.get(finished["result_url"])
    assert result.status_code == 200
    body = result.json()
    assert body["claims"][0]["verdict"] == "supported"
    assert body["run"]["kb"]["name"] == "test-kb"

    report = api_client.get(finished["report_url"])
    assert report.status_code == 200
    assert "支持" in report.text


def test_invalid_kb_and_too_long(api_client: TestClient) -> None:
    missing = api_client.post(
        "/api/checks",
        json={"article_text": "x", "kb": "does-not-exist"},
    )
    assert missing.status_code == 404

    too_long = api_client.post(
        "/api/checks",
        json={"article_text": "x" * 200_001, "kb": "demo"},
    )
    assert too_long.status_code == 422


def test_unindexed_kb_returns_conflict(kb_dir: Path, tmp_path: Path) -> None:
    root = _kb_root(tmp_path, kb_dir, index=False)
    with _client(tmp_path, root) as client:
        response = client.post(
            "/api/checks",
            json={"article_text": "x", "kb": "demo"},
        )
        assert response.status_code == 409


def test_index_endpoint(kb_dir: Path, tmp_path: Path) -> None:
    root = _kb_root(tmp_path, kb_dir, index=False)
    with _client(tmp_path, root) as client:
        response = client.post("/api/kbs/demo/index")
        assert response.status_code == 200, response.text
        assert response.json()["documents"] == 2
        info = client.get("/api/kbs/demo").json()
        assert info["indexed"] is True


def test_confidential_requires_override(kb_dir: Path, tmp_path: Path) -> None:
    root = _kb_root(tmp_path, kb_dir, sensitivity="confidential")
    with _client(tmp_path, root) as client:
        denied = client.post(
            "/api/checks",
            json={"article_text": "x", "kb": "demo"},
        )
        assert denied.status_code == 403

        allowed = client.post(
            "/api/checks",
            json={"article_text": "x", "kb": "demo", "allow_confidential": True},
        )
        assert allowed.status_code == 202, allowed.text


def test_root_fallback(api_client: TestClient) -> None:
    response = api_client.get("/")
    assert response.status_code == 200
    assert "ReviewPilot API" in response.text
    assert "前端尚未构建" in response.text


def test_web_index_is_not_cached(kb_dir: Path, tmp_path: Path) -> None:
    root = _kb_root(tmp_path, kb_dir)
    dist = tmp_path / "web-dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<html><body>web-index</body></html>", encoding="utf-8"
    )
    with _client(tmp_path, root, web_dist=dist) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "web-index" in response.text
        assert "no-cache" in response.headers.get("cache-control", "")
