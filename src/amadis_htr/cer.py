"""Character and word error rates, with the definition pinned.

Whitespace counts as a character. Runs of whitespace collapse to one space
before comparison, so a line break where the reference has a space is not an
error while a lost word boundary is.
"""

import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

import jiwer

from amadis_htr.fold import fold

_WHITESPACE = re.compile(r"\s+")


def flatten(text: str) -> str:
    """Collapse whitespace runs to one space and strip the ends."""
    return _WHITESPACE.sub(" ", text).strip()


@dataclass(frozen=True)
class PageScore:
    page_id: str
    cer: float
    wer: float
    ref_chars: int
    ref_words: int
    char_edits: int
    word_edits: int


def score_page(
    page_id: str, reference: str, hypothesis: str, *, folded: bool = False
) -> PageScore:
    """Score one page. `folded` applies the declared fold to both sides."""
    ref, hyp = flatten(reference), flatten(hypothesis)
    if folded:
        ref, hyp = fold(ref), fold(hyp)

    chars = jiwer.process_characters(ref, hyp)
    words = jiwer.process_words(ref, hyp)

    char_edits = chars.substitutions + chars.deletions + chars.insertions
    ref_chars = chars.substitutions + chars.deletions + chars.hits
    word_edits = words.substitutions + words.deletions + words.insertions
    ref_words = words.substitutions + words.deletions + words.hits

    return PageScore(
        page_id=page_id,
        cer=char_edits / ref_chars if ref_chars else 0.0,
        wer=word_edits / ref_words if ref_words else 0.0,
        ref_chars=ref_chars,
        ref_words=ref_words,
        char_edits=char_edits,
        word_edits=word_edits,
    )


def aggregate(scores: Sequence[PageScore]) -> tuple[float, float]:
    """Character-weighted CER and word-weighted WER over pages.

    Weighted rather than averaged so that a short clean page cannot offset a
    long bad one.
    """
    ref_chars = sum(s.ref_chars for s in scores)
    ref_words = sum(s.ref_words for s in scores)
    char_edits = sum(s.char_edits for s in scores)
    word_edits = sum(s.word_edits for s in scores)
    return (
        char_edits / ref_chars if ref_chars else 0.0,
        word_edits / ref_words if ref_words else 0.0,
    )


def substitution_counts(reference: str, hypothesis: str) -> Counter:
    """Count substituted character pairs, for the error-analysis table."""
    ref, hyp = flatten(reference), flatten(hypothesis)
    out: Counter = Counter()
    result = jiwer.process_characters(ref, hyp)
    for chunks in result.alignments:
        for chunk in chunks:
            if chunk.type != "substitute":
                continue
            r = ref[chunk.ref_start_idx : chunk.ref_end_idx]
            h = hyp[chunk.hyp_start_idx : chunk.hyp_end_idx]
            for a, b in zip(r, h):
                out[(a, b)] += 1
    return out
