"""Typer entry point.

M0 skeleton: the commands are registered with their final arguments but exit
with code 3 until their milestones land. This keeps ``--help`` and packaging
honest without pretending the verification pipeline exists.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from dotenv import load_dotenv

from reviewpilot import __version__
from reviewpilot.config import load_config, stricter_sensitivity
from reviewpilot.eval import EvalError, run_eval
from reviewpilot.index.fts import build_index, inspect_index
from reviewpilot.ingest.manifest import ManifestError, load_manifest
from reviewpilot.llm.provider import DeepSeekProvider, LLMError
from reviewpilot.pipeline import CheckOptions, run_check


def _configure_console() -> None:
    """Make Chinese help/report text readable on Windows consoles.

    Python defaults to the legacy code page (e.g. GBK) when stdout is a
    console. Git Bash/Windows Terminal expect UTF-8, so reconfigure the
    streams and switch the console code page where possible. Only called by
    the CLI entry point, never on import.
    """
    if sys.platform == "win32" and (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

app = typer.Typer(
    name="reviewpilot",
    help="逐句核验 AI 技术文章：有据则支持，无据则存疑。",
    no_args_is_help=True,
    add_completion=False,
)
kb_app = typer.Typer(help="知识库管理。", no_args_is_help=True)
app.add_typer(kb_app, name="kb")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"reviewpilot {__version__}")
        raise typer.Exit()


def _not_implemented(command: str) -> None:
    typer.secho(
        f"{command} 尚未实现：该命令属于 M3 评测阶段；"
        "M0–M2 的 `kb index` / `kb inspect` / `check` 已可用。",
        fg=typer.colors.YELLOW,
        err=True,
    )
    raise typer.Exit(code=3)


def _resolve_kb(kb: Optional[Path], config: Optional[Path]) -> Path:
    """Explicit --kb wins; otherwise use the config (or its default)."""
    if kb is not None:
        return kb
    return load_config(config).kb


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="显示版本并退出。",
        ),
    ] = False,
) -> None:
    """ReviewPilot 命令行入口。"""
    load_dotenv()
    _ = version


@kb_app.command("index")
def kb_index(
    kb: Annotated[Optional[Path], typer.Option("--kb", "-k", help="知识库目录。")] = None,
    config: Annotated[Optional[Path], typer.Option("--config", help="配置文件路径。")] = None,
) -> None:
    """校验 manifest 并重建 FTS5 索引。"""
    try:
        stats = build_index(_resolve_kb(kb, config))
    except (ManifestError, FileNotFoundError, ValueError, OSError, sqlite3.Error) as exc:
        typer.secho(f"索引失败：{exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=3) from exc

    typer.echo(f"索引完成：{stats.documents} 篇文档，{stats.chunks} 个块")
    typer.echo(
        f"manifest：{stats.manifest_name} {stats.manifest_version}"
        f"（{stats.sensitivity}）"
    )
    typer.echo(f"输出：{stats.index_path}")


@kb_app.command("inspect")
def kb_inspect(
    kb: Annotated[Optional[Path], typer.Option("--kb", "-k", help="知识库目录。")] = None,
    config: Annotated[Optional[Path], typer.Option("--config", help="配置文件路径。")] = None,
) -> None:
    """查看知识库版本、文档数与索引状态。"""
    try:
        inspection = inspect_index(_resolve_kb(kb, config))
    except (FileNotFoundError, OSError, sqlite3.Error) as exc:
        typer.secho(f"读取索引失败：{exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=3) from exc

    typer.echo(f"索引：{inspection.index_path}")
    typer.echo(f"文档：{inspection.documents}  块：{inspection.chunks}")
    for key in (
        "manifest_name",
        "manifest_version",
        "manifest_effective_date",
        "manifest_sha256",
        "sensitivity",
        "built_at",
        "tokenizer",
    ):
        value = inspection.meta.get(key)
        if value is not None:
            typer.echo(f"{key}：{value}")


@app.command("check")
def check(
    article: Annotated[Path, typer.Argument(help="待核验文章（.md / .txt）。")],
    kb: Annotated[Optional[Path], typer.Option("--kb", "-k", help="知识库目录。")] = None,
    out: Annotated[Optional[Path], typer.Option("--out", "-o", help="运行输出目录。")] = None,
    config: Annotated[Optional[Path], typer.Option("--config", help="配置文件路径。")] = None,
    no_store_article: Annotated[
        bool,
        typer.Option("--no-store-article", help="不在运行产物中保存原文副本。"),
    ] = False,
    allow_confidential: Annotated[
        bool,
        typer.Option("--allow-confidential", help="允许将 internal/confidential 语料发送到云端。"),
    ] = False,
    concurrency: Annotated[
        int,
        typer.Option("--concurrency", min=1, max=64, help="并发模型请求数。"),
    ] = 4,
) -> None:
    """核验一篇文章，输出 report.md 与 result.json。"""
    if not article.exists() or not article.is_file():
        typer.secho(f"文章不存在：{article}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=3)

    try:
        app_config = load_config(config)
        kb_dir = _resolve_kb(kb, config)
        manifest = load_manifest(kb_dir)
        effective = stricter_sensitivity(
            app_config.sensitivity, manifest.manifest.sensitivity
        )
        if effective != "public" and not allow_confidential:
            typer.secho(
                f"知识库敏感级别为 {effective}，默认拒绝发送到云端；"
                "如确认要运行，请加 --allow-confidential。",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=3)

        provider = DeepSeekProvider()
        typer.echo(
            "数据边界：发送文章全文 + 检索到的 KB 片段到 DeepSeek；"
            f"KB 不整库上传；敏感级别 {effective}。"
        )
        result, run_dir = run_check(
            CheckOptions(
                article_path=article,
                kb_dir=kb_dir,
                out_dir=out or Path("runs"),
                config=app_config,
                provider=provider,
                store_article=not no_store_article,
                concurrency=concurrency,
            )
        )
    except (ManifestError, FileNotFoundError, LLMError, ValueError, OSError, sqlite3.Error) as exc:
        typer.secho(f"核验失败：{exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=3) from exc

    summary = result.summary
    typer.echo(
        f"核验完成：支持 {summary.supported} / 冲突 {summary.conflict} / "
        f"存疑 {summary.uncertain} / 未核验 {summary.unverified}"
    )
    typer.echo(f"报告：{run_dir / 'report.md'}")
    typer.echo(f"结果：{run_dir / 'result.json'}")

    if summary.claims_total == 0:
        typer.secho("未抽取到可判定主张。", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=4)
    if summary.conflict:
        raise typer.Exit(code=2)
    if summary.uncertain:
        raise typer.Exit(code=1)


@app.command("eval")
def eval_gold(
    gold: Annotated[Path, typer.Option("--gold", help="金标集目录。")],
    kb: Annotated[Optional[Path], typer.Option("--kb", "-k", help="知识库目录。")] = None,
    config: Annotated[Optional[Path], typer.Option("--config", help="配置文件路径。")] = None,
    out: Annotated[Optional[Path], typer.Option("--out", "-o", help="结果输出目录。")] = None,
    concurrency: Annotated[
        int,
        typer.Option("--concurrency", min=1, max=64, help="并发模型请求数。"),
    ] = 4,
    allow_confidential: Annotated[
        bool,
        typer.Option("--allow-confidential", help="允许将 internal/confidential 语料发送到云端。"),
    ] = False,
) -> None:
    """跑金标集，计算假支持率、一致率与冲突召回。"""
    try:
        app_config = load_config(config)
        app_config = app_config.model_copy(update={"concurrency": concurrency})
        kb_dir = _resolve_kb(kb, config)
        manifest = load_manifest(kb_dir)
        effective = stricter_sensitivity(
            app_config.sensitivity, manifest.manifest.sensitivity
        )
        if effective != "public" and not allow_confidential:
            typer.secho(
                f"知识库敏感级别为 {effective}，默认拒绝发送到云端；"
                "如确认要运行，请加 --allow-confidential。",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=3)

        provider = DeepSeekProvider()
        typer.echo(
            "数据边界：发送文章全文 + 检索到的 KB 片段到 DeepSeek；"
            f"KB 不整库上传；敏感级别 {effective}。"
        )
        report, eval_dir, passed = run_eval(
            gold,
            kb_dir,
            app_config,
            provider,
            out or Path("eval/runs"),
        )
    except (EvalError, ManifestError, FileNotFoundError, LLMError, ValueError, OSError, sqlite3.Error) as exc:
        typer.secho(f"评测失败：{exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=3) from exc

    aggregate = report["aggregate"]
    typer.echo(
        f"金标评测：金标 {aggregate['gold_total']} 条，匹配 {aggregate['matched']}，"
        f"假支持 {aggregate['false_support']}，未匹配支持 {aggregate['ungraded_support']}"
    )
    typer.echo(
        f"支持一致率 {aggregate['supported_agreement']:.1%} / "
        f"冲突召回 {aggregate['conflict_recall']:.1%} / "
        f"覆盖率 {aggregate['coverage']:.1%} / "
        f"证据逐字 {aggregate['evidence_exactness']:.1%}"
    )
    typer.echo(f"门槛：{'通过' if passed else '未通过'}")
    typer.echo(f"报告：{eval_dir / 'eval-report.md'}")
    if not passed:
        raise typer.Exit(code=1)


def run() -> None:
    """Console-script entry point: configure output encoding, then run."""
    _configure_console()
    app()


if __name__ == "__main__":
    run()
