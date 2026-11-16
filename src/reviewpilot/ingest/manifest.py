"""Knowledge-base manifest loading and validation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

Format = Literal["markdown", "html", "text"]
Sensitivity = Literal["public", "internal", "confidential"]


class ManifestError(ValueError):
    """Raised when a knowledge-base manifest or its sources are invalid."""


class SourceSpec(BaseModel):
    path: str
    title: str
    format: Format
    url: Optional[str] = None
    retrieved_at: Optional[date] = None
    version: Optional[str] = None
    sha256: Optional[str] = None


class Manifest(BaseModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    effective_date: date
    sensitivity: Sensitivity = "public"
    sources: list[SourceSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_source_paths(self) -> "Manifest":
        paths = [source.path for source in self.sources]
        if len(paths) != len(set(paths)):
            raise ValueError("manifest 中存在重复的 source.path")
        return self


@dataclass(frozen=True)
class LoadedSource:
    spec: SourceSpec
    path: Path
    sha256: str
    text: str


@dataclass(frozen=True)
class LoadedManifest:
    manifest: Manifest
    manifest_path: Path
    manifest_sha256: str
    sources: tuple[LoadedSource, ...]


def load_manifest(kb_dir: Path) -> LoadedManifest:
    """Load and validate ``kb_dir/manifest.yaml`` plus every source file.

    ``kb_dir`` is resolved before path checks. Sources must stay inside the
    KB root; a source's optional ``sha256`` is verified when present.
    """
    kb_dir = kb_dir.resolve()
    manifest_path = kb_dir / "manifest.yaml"
    if not manifest_path.exists():
        alt = kb_dir / "manifest.yml"
        if alt.exists():
            manifest_path = alt
        else:
            raise ManifestError(f"找不到 manifest.yaml：{kb_dir}")

    try:
        raw_bytes = manifest_path.read_bytes()
    except OSError as exc:
        raise ManifestError(f"无法读取 manifest：{manifest_path}（{exc}）") from exc

    manifest_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    try:
        raw = yaml.safe_load(raw_bytes.decode("utf-8")) or {}
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ManifestError(f"manifest 不是有效的 UTF-8 YAML：{exc}") from exc

    try:
        manifest = Manifest.model_validate(raw)
    except ValidationError as exc:
        raise ManifestError(f"manifest 校验失败：{exc}") from exc

    loaded: list[LoadedSource] = []
    for spec in manifest.sources:
        relative = Path(spec.path)
        if relative.is_absolute():
            raise ManifestError(f"source.path 必须是相对路径：{spec.path}")
        source_path = (kb_dir / relative).resolve()
        if not source_path.is_relative_to(kb_dir):
            raise ManifestError(f"source.path 逃逸出 KB 目录：{spec.path}")
        if not source_path.is_file():
            raise ManifestError(f"source 文件不存在：{source_path}")

        try:
            data = source_path.read_bytes()
        except OSError as exc:
            raise ManifestError(f"无法读取 source：{source_path}（{exc}）") from exc
        actual_sha256 = hashlib.sha256(data).hexdigest()
        if spec.sha256 and spec.sha256.lower() != actual_sha256:
            raise ManifestError(
                f"source 哈希不匹配：{spec.path}（manifest={spec.sha256}, actual={actual_sha256}）"
            )
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ManifestError(f"source 不是有效的 UTF-8 文本：{spec.path}") from exc

        loaded.append(
            LoadedSource(spec=spec, path=source_path, sha256=actual_sha256, text=text)
        )

    return LoadedManifest(
        manifest=manifest,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        sources=tuple(loaded),
    )
