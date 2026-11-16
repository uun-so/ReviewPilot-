"""Shared domain models for the verification pipeline and result.json."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Verdict = Literal["supported", "conflict", "uncertain"]
Relation = Literal["supports", "contradicts"]


class Sentence(BaseModel):
    sentence_id: str
    text: str
    char_start: int
    char_end: int
    block_kind: str = "paragraph"
    heading_path: str = ""
    claim_ids: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    doc_id: str
    doc_title: str
    source_path: str
    source_version: str | None = None
    quote: str
    char_start: int
    char_end: int
    relation: Relation
    used_for_verdict: bool = True
    chunk_id: str = ""


class Claim(BaseModel):
    claim_id: str
    quote: str
    char_start: int
    char_end: int
    sentence_ids: list[str] = Field(default_factory=list)
    verdict: Verdict = "uncertain"
    reason: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    gates: dict[str, str] = Field(default_factory=dict)
    usage: dict[str, int] = Field(default_factory=dict)


class Unverified(BaseModel):
    sentence_id: str
    text: str
    reason: str


class ArticleMeta(BaseModel):
    path: str
    sha256: str
    char_count: int


class KbMeta(BaseModel):
    name: str
    version: str
    manifest_sha256: str


class ModelMeta(BaseModel):
    judge: str
    verifier: str
    judge_effort: str
    verifier_effort: str


class RunMeta(BaseModel):
    run_id: str
    created_at: str
    article: ArticleMeta
    kb: KbMeta
    models: ModelMeta
    prompt_version: str
    code_version: str


class Summary(BaseModel):
    claims_total: int
    supported: int
    conflict: int
    uncertain: int
    unverified: int


class CheckResult(BaseModel):
    schema_version: str = "1.0"
    run: RunMeta
    summary: Summary
    sentences: list[Sentence]
    claims: list[Claim]
    unverified: list[Unverified]


class ExtractedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote: str
    kind: Literal[
        "checkable", "opinion", "prediction", "definition", "rhetoric", "code", "other"
    ]
    reason: str


class ExtractedSentence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentence_id: str
    claims: list[ExtractedClaim]


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentences: list[ExtractedSentence]


class JudgeEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    quote: str
    relation: Relation


class JudgeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Verdict
    basis_doc_id: str
    reason: str
    evidence: list[JudgeEvidence]


class VerifyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["supported", "conflict", "insufficient"]
    reason: str
