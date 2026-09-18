"""Percentile bootstrap over pages.

Pages are the resampling unit, not characters: a page's errors are correlated,
because a badly segmented or badly inked page fails as a whole.
"""

from typing import Sequence

import numpy as np

from amadis_htr.cer import PageScore


def bootstrap_cer(
    scores: Sequence[PageScore],
    *,
    resamples: int = 10_000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Return (point estimate, lower bound, upper bound) for the CER."""
    if not scores:
        return (0.0, 0.0, 0.0)

    edits = np.array([s.char_edits for s in scores], dtype=float)
    chars = np.array([s.ref_chars for s in scores], dtype=float)
    point = float(edits.sum() / chars.sum()) if chars.sum() else 0.0

    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(scores), size=(resamples, len(scores)))
    totals = chars[draws].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        stats = np.where(totals > 0, edits[draws].sum(axis=1) / totals, 0.0)

    low, high = np.quantile(stats, [alpha / 2, 1 - alpha / 2])
    return (point, float(low), float(high))
