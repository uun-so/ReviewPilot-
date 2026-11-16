"""Programmatic anchoring of extracted quotes to the article text.

The model never supplies offsets. If a quote cannot be found inside (or
overlapping) its source sentence, it is not silently accepted: the item is
reported as unverified with ``anchor_failed``.
"""

from __future__ import annotations

from dataclasses import dataclass

from reviewpilot.domain import ExtractionResult, Sentence, Unverified
from reviewpilot.ingest.blocks import Document


@dataclass(frozen=True)
class AnchoredClaim:
    sentence_id: str
    quote: str
    char_start: int
    char_end: int


def locate_quote(
    text: str, quote: str, *, hint_start: int, hint_end: int
) -> tuple[int, int] | None:
    """Find ``quote`` inside the hint range, else accept a global occurrence
    only if it overlaps the hint range. Never anchor to an unrelated duplicate.
    """
    if not quote:
        return None
    local = text.find(quote, hint_start, hint_end)
    if local != -1:
        return local, local + len(quote)

    position = text.find(quote)
    while position != -1:
        if position < hint_end and position + len(quote) > hint_start:
            return position, position + len(quote)
        position = text.find(quote, position + 1)
    return None


def anchor_claims(
    document: Document,
    sentences: list[Sentence],
    extraction: ExtractionResult,
) -> tuple[list[AnchoredClaim], list[Unverified]]:
    by_sentence = {item.sentence_id: item for item in extraction.sentences}
    anchored: list[AnchoredClaim] = []
    unverified: list[Unverified] = []
    seen: set[tuple[str, str, int, int]] = set()

    for sentence in sentences:
        entry = by_sentence.get(sentence.sentence_id)
        if entry is None:
            unverified.append(
                Unverified(
                    sentence_id=sentence.sentence_id,
                    text=sentence.text,
                    reason="extraction_failed",
                )
            )
            continue

        checkable = [
            claim
            for claim in entry.claims
            if claim.kind == "checkable" and claim.quote.strip()
        ]
        sentence_anchored = 0
        for claim in checkable:
            quote = claim.quote.strip()
            span = locate_quote(
                document.text,
                quote,
                hint_start=sentence.char_start,
                hint_end=sentence.char_end,
            )
            if span is None:
                unverified.append(
                    Unverified(
                        sentence_id=sentence.sentence_id,
                        text=quote,
                        reason="anchor_failed",
                    )
                )
                continue
            start, end = span
            key = (sentence.sentence_id, quote, start, end)
            if key in seen:
                continue
            seen.add(key)
            anchored.append(
                AnchoredClaim(
                    sentence_id=sentence.sentence_id,
                    quote=quote,
                    char_start=start,
                    char_end=end,
                )
            )
            sentence_anchored += 1

        if sentence_anchored:
            continue

        if checkable:
            # All checkable claims failed anchoring; do not also report the
            # sentence as an opinion/prediction.
            continue

        reason = entry.claims[0].kind if entry.claims else "other"
        unverified.append(
            Unverified(
                sentence_id=sentence.sentence_id,
                text=sentence.text,
                reason=reason,
            )
        )

    return anchored, unverified
