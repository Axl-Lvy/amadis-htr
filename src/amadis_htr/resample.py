"""Percentile bootstrap over pages.

Pages are the resampling unit, not characters: a page's errors are correlated,
because a badly segmented or badly inked page fails as a whole.
"""

from typing import Mapping, Sequence

import numpy as np


def bootstrap_stratified_rate(
    strata: Mapping[str, tuple[Sequence[tuple[str, int, int]], float]],
    *,
    resamples: int = 10_000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """A weighted rate across strata, `{name: (per-page counts, weight)}`.

    For a design that samples equally from unequal strata. Summing the strata
    and dividing weights each one by how much of it was *sampled*, which is a
    statement about the draw rather than about the population. Each stratum's
    own rate is computed instead, and the weighted sum is taken, so the figure
    describes the frame the weights come from.

    The resampling is stratified for the same reason: pages are drawn with
    replacement inside each stratum and the strata are recombined with the same
    fixed weights, so the interval carries the design rather than ignoring it.

    Weights are normalised, so a caller may pass raw sizes.
    """
    if not strata:
        return (0.0, 0.0, 0.0)
    total_weight = sum(weight for _, weight in strata.values())
    if total_weight <= 0:
        raise ValueError(
            "the stratum weights sum to zero, so the weighted rate has no "
            "denominator. A frame with nothing in it has no rate."
        )

    rng = np.random.default_rng(seed)
    point = 0.0
    draws = np.zeros(resamples, dtype=float)
    for name in sorted(strata):
        counts, weight = strata[name]
        share = weight / total_weight
        if not counts:
            raise ValueError(
                f"stratum {name!r} carries weight {weight} but no sampled "
                "pages, so its rate is unobserved and the weighted total "
                "cannot be formed."
            )
        numerators = np.array([n for _, n, _ in counts], dtype=float)
        denominators = np.array([d for _, _, d in counts], dtype=float)
        bottom = denominators.sum()
        point += share * (numerators.sum() / bottom if bottom else 0.0)

        picks = rng.integers(0, len(counts), size=(resamples, len(counts)))
        totals = denominators[picks].sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            rates = np.where(totals > 0, numerators[picks].sum(axis=1) / totals, 0.0)
        draws += share * rates

    low, high = np.quantile(draws, [alpha / 2, 1 - alpha / 2])
    return (float(point), float(low), float(high))


def bootstrap_rate(
    counts: Sequence[tuple[str, int, int]],
    *,
    resamples: int = 10_000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Interval for a ratio of two per-page totals, `(id, numerator, denominator)`.

    A percentile bootstrap whose unit is the page:
    E2's acceptance rate is a ratio of counts whose unit is the page, because
    the lines on one page share a scan and a stretch of type wear and their
    verdicts are correlated. Resampling lines would report an interval narrower
    than the evidence supports.

    An unobserved rate is `nan`, not 0.0: a stratum with no sampled pages has
    no acceptance rate, and returning zero would put a measured 0% and a
    measurement that was never taken in the same cell.

    A resample drawing only empty-denominator pages is dropped rather than
    scored 0, which would drag the lower bound down. On E2's frame it cannot
    fire, every frame page carrying at least one span, but a fallback that is
    wrong in principle is wrong when the frame changes.
    """
    if not counts:
        return (float("nan"), float("nan"), float("nan"))

    numerators = np.array([n for _, n, _ in counts], dtype=float)
    denominators = np.array([d for _, _, d in counts], dtype=float)
    total = denominators.sum()
    point = float(numerators.sum() / total) if total else 0.0

    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(counts), size=(resamples, len(counts)))
    totals = denominators[draws].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        stats = numerators[draws].sum(axis=1) / totals
    stats = stats[totals > 0]
    if not stats.size:
        return (point, float("nan"), float("nan"))

    low, high = np.quantile(stats, [alpha / 2, 1 - alpha / 2])
    return (point, float(low), float(high))
