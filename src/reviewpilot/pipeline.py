"""End-to-end check pipeline: article -> sentences -> claims -> judge -> report."""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from reviewpilot import __version__
from reviewpilot.claims.anchor import AnchoredClaim, anchor_claims
from reviewpilot.claims.extract import extract_claims
from reviewpilot.claims.sentences import segment_document
from reviewpilot.config import AppConfig
from reviewpilot.domain import (
    ArticleMeta,
    CheckResult,
    Claim,
    KbMeta,
    ModelMeta,
    RunMeta,
    Summary,
    Unverified,
)
from reviewpilot.index.fts import search_index
from reviewpilot.ingest.blocks import Document
from reviewpilot.ingest.html import parse_html
from reviewpilot.ingest.manifest import load_manifest
from reviewpilot.ingest.markdown import parse_markdown
from reviewpilot.ingest.text import parse_text
from reviewpilot.judge.judge import judge_claim
from reviewpilot.llm.provider import LLMProvider
from reviewpilot.prompts import PROMPT_VERSION
from reviewpilot.report.writer import write_outputs


@dataclass(frozen=True)
class CheckOptions:
    article_path: Path
    kb_dir: Path
    out_dir: Path
    config: AppConfig
    provider: LLMProvider
    store_article: bool = True
    concurrency: int = 8


def load_article(path: Path) -> Document:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"文章不是有效的 UTF-8 文本：{path}") from exc
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        blocks = parse_markdown(text)
        fmt = "markdown"
        title = path.stem
    elif suffix in {".html", ".htm"}:
        text, blocks, html_title = parse_html(text)
        fmt = "html"
        title = html_title or path.stem
    else:
        blocks = parse_text(text)
        fmt = "text"
        title = path.stem

    if not blocks:
        raise ValueError(f"文章未解析到任何文本块：{path}")

    return Document(
        doc_id="article",
        title=title,
        source_path=str(path),
        source_version=None,
        format=fmt,
        sha256=hashlib.sha256(raw).hexdigest(),
        text=text,
        blocks=tuple(blocks),
    )


def run_check(options: CheckOptions) -> tuple[CheckResult, Path]:
    article = load_article(options.article_path)
    manifest = load_manifest(options.kb_dir)
    sentences = segment_document(article)

    extraction, extraction_usage = extract_claims(
        options.provider,
        sentences,
        model=options.config.models.extraction,
    )
    anchored, unverified = anchor_claims(article, sentences, extraction)

    trace: list[dict] = [
        {
            "event": "extraction",
            "sentences": len(sentences),
            "claims": len(anchored),
            "unverified": len(unverified),
            "usage": extraction_usage,
        }
    ]

    def judge_one(item: AnchoredClaim):
        retrieved = search_index(options.kb_dir, item.quote, limit=6)
        outcome = judge_claim(options.provider, item, retrieved, options.config.models)
        return item, retrieved, outcome

    judged = []
    if options.concurrency > 1 and len(anchored) > 1:
        with ThreadPoolExecutor(max_workers=options.concurrency) as pool:
            futures = {pool.submit(judge_one, item): item for item in anchored}
            for future in as_completed(futures):
                judged.append(future.result())
        order = {item: index for index, item in enumerate(anchored)}
        judged.sort(key=lambda entry: order[entry[0]])
    else:
        judged = [judge_one(item) for item in anchored]

    claims: list[Claim] = []
    sentence_claim_ids: dict[str, list[str]] = {}
    for index, (item, retrieved, outcome) in enumerate(judged, start=1):
        claim_id = f"c{index}"
        claims.append(
            Claim(
                claim_id=claim_id,
                quote=item.quote,
                char_start=item.char_start,
                char_end=item.char_end,
                sentence_ids=[item.sentence_id],
                verdict=outcome.verdict,
                reason=outcome.reason,
                evidence=outcome.evidence,
                gates=outcome.gates,
                usage=outcome.usage,
            )
        )
        sentence_claim_ids.setdefault(item.sentence_id, []).append(claim_id)
        trace.append(
            {
                "event": "claim",
                "claim_id": claim_id,
                "sentence_id": item.sentence_id,
                "verdict": outcome.verdict,
                "gates": outcome.gates,
                "retrieved": [chunk["chunk_id"] for chunk in retrieved],
                "usage": outcome.usage,
            }
        )

    sentences_out = [
        sentence.model_copy(update={"claim_ids": sentence_claim_ids.get(sentence.sentence_id, [])})
        for sentence in sentences
    ]

    supported = sum(1 for claim in claims if claim.verdict == "supported")
    conflict = sum(1 for claim in claims if claim.verdict == "conflict")
    uncertain = sum(1 for claim in claims if claim.verdict == "uncertain")

    now = datetime.now(timezone.utc)
    run_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{article.sha256[:8]}"
    result = CheckResult(
        run=RunMeta(
            run_id=run_id,
            created_at=now.isoformat(timespec="seconds"),
            article=ArticleMeta(
                path=str(options.article_path),
                sha256=article.sha256,
                char_count=len(article.text),
            ),
            kb=KbMeta(
                name=manifest.manifest.name,
                version=manifest.manifest.version,
                manifest_sha256=manifest.manifest_sha256,
            ),
            models=ModelMeta(
                judge=options.config.models.judge,
                verifier=options.config.models.verifier,
                judge_effort=options.config.models.judge_effort,
                verifier_effort=options.config.models.verifier_effort,
            ),
            prompt_version=PROMPT_VERSION,
            code_version=__version__,
        ),
        summary=Summary(
            claims_total=len(claims),
            supported=supported,
            conflict=conflict,
            uncertain=uncertain,
            unverified=len(unverified),
        ),
        sentences=sentences_out,
        claims=claims,
        unverified=[Unverified(**item.model_dump()) for item in unverified],
    )

    run_dir = options.out_dir / run_id
    write_outputs(
        result,
        run_dir,
        article_path=options.article_path,
        store_article=options.store_article,
        trace_events=trace,
    )
    return result, run_dir
