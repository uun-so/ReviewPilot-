"""Configuration models and loader.

The effective sensitivity is the stricter of the manifest and the config
(see docs/adr/0011-privacy-provider-boundary.md).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field

Sensitivity = Literal["public", "internal", "confidential"]
Effort = Literal["none", "low", "high", "max"]

_SENSITIVITY_RANK: dict[Sensitivity, int] = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
}


class ModelConfig(BaseModel):
    extraction: str = "deepseek-flash"
    query: str = "deepseek-flash"
    judge: str = "deepseek-v4-pro"
    verifier: str = "deepseek-v4-pro"
    judge_effort: Effort = "none"
    verifier_effort: Effort = "low"


class ReportConfig(BaseModel):
    annotated: bool = True


class AppConfig(BaseModel):
    kb: Path = Path("kb/demo")
    sensitivity: Sensitivity = "public"
    concurrency: int = Field(default=4, ge=1, le=64)
    models: ModelConfig = Field(default_factory=ModelConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)


def stricter_sensitivity(a: Sensitivity, b: Sensitivity) -> Sensitivity:
    """Return the stricter of two sensitivity levels."""
    return a if _SENSITIVITY_RANK[a] >= _SENSITIVITY_RANK[b] else b


def load_config(path: Optional[Path] = None) -> AppConfig:
    """Load ``reviewpilot.yaml``; missing default file yields defaults.

    An explicitly supplied path must exist. Relative ``kb`` paths are resolved
    against the config file's directory, not the current working directory.
    """
    candidate = path or Path("reviewpilot.yaml")
    if not candidate.exists():
        if path is not None:
            raise FileNotFoundError(f"config file not found: {candidate}")
        return AppConfig()

    raw = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
    config = AppConfig.model_validate(raw)
    if not config.kb.is_absolute():
        config = config.model_copy(update={"kb": (candidate.parent / config.kb).resolve()})
    return config
