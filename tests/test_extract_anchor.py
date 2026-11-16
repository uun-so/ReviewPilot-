from reviewpilot.claims.anchor import anchor_claims
from reviewpilot.claims.extract import extract_claims
from reviewpilot.claims.sentences import segment_document
from reviewpilot.domain import (
    ExtractedClaim,
    ExtractedSentence,
    ExtractionResult,
    Sentence,
)
from reviewpilot.ingest.blocks import Block, Document
from reviewpilot.ingest.markdown import parse_markdown

from tests.fakes import FakeProvider


def _document(raw: str) -> Document:
    blocks = parse_markdown(raw)
    return Document(
        doc_id="article",
        title="article",
        source_path="article.md",
        source_version=None,
        format="markdown",
        sha256="x",
        text=raw,
        blocks=tuple(blocks),
    )


def test_segmentation_skips_code_blocks() -> None:
    raw = "# T\n\n第一句。第二句！\n\n```python\nprint('x')\n```\n\n第三句。\n"
    sentences = segment_document(_document(raw))
    assert [s.text for s in sentences] == ["第一句。", "第二句！", "第三句。"]
    for sentence in sentences:
        assert raw[sentence.char_start : sentence.char_end] == sentence.text


def test_extraction_and_anchor() -> None:
    raw = "HTTPConnection 默认超时为 30 秒。\n"
    document = _document(raw)
    sentences = segment_document(document)
    provider = FakeProvider(
        lambda **kwargs: (
            {
                "sentences": [
                    {
                        "sentence_id": sentences[0].sentence_id,
                        "claims": [
                                {
                                    "quote": "默认超时为 30 秒。",
                                    "kind": "checkable",
                                    "reason": "",
                                }
                        ],
                    }
                ]
            },
            {"input_tokens": 1, "output_tokens": 1},
        )
    )
    extraction, usage = extract_claims(provider, sentences, model="deepseek-flash")
    anchored, unverified = anchor_claims(document, sentences, extraction)
    assert usage["input_tokens"] == 1
    assert len(anchored) == 1
    assert raw[anchored[0].char_start : anchored[0].char_end] == "默认超时为 30 秒。"
    assert unverified == []


def test_anchor_failure_and_non_claim() -> None:
    document = Document(
        doc_id="article",
        title="article",
        source_path="article.md",
        source_version=None,
        format="text",
        sha256="x",
        text="原句。",
        blocks=(Block("paragraph", "原句。", 0, 3),),
    )
    sentences = [Sentence(sentence_id="s1", text="原句。", char_start=0, char_end=3)]
    extraction = ExtractionResult(
        sentences=[
            ExtractedSentence(
                sentence_id="s1",
                claims=[
                    ExtractedClaim(quote="不存在的句子。", kind="checkable", reason=""),
                    ExtractedClaim(quote="原句。", kind="opinion", reason="主观判断"),
                ],
            )
        ]
    )
    anchored, unverified = anchor_claims(document, sentences, extraction)
    assert anchored == []
    reasons = {item.reason for item in unverified}
    assert "anchor_failed" in reasons
