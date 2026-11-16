from reviewpilot.ingest.blocks import Document
from reviewpilot.index.chunker import chunk_document
from reviewpilot.ingest.markdown import parse_markdown


def test_oversized_block_splits_and_spans_stay_valid() -> None:
    raw = "# Title\n\n" + "这是一个很长的句子。" * 100 + "\n"
    blocks = parse_markdown(raw)
    document = Document(
        doc_id="doc",
        title="Title",
        source_path="doc.md",
        source_version=None,
        format="markdown",
        sha256="x",
        text=raw,
        blocks=tuple(blocks),
    )
    chunks = chunk_document(document, target_tokens=200, max_tokens=220)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.text.strip()
        assert 0 <= chunk.char_start < chunk.char_end <= len(raw)
        assert chunk.token_count <= 260
