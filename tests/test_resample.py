import math

import pytest

from amadis_htr.resample import bootstrap_rate, bootstrap_stratified_rate


def _stratum(rate: float, pages: int = 20, per_page: int = 10):
    """`pages` pages, each carrying `per_page` lines at the given rate."""
    hits = round(per_page * rate)
    return [(f"p{i}", hits, per_page) for i in range(pages)]


def test_the_weighted_rate_follows_the_frame_and_not_the_draw():
    # Equal draws from unequal strata. Summing and dividing would give 0.5;
    # the frame weights A at a quarter, so the answer is 0.25*0.8 + 0.75*0.2.
    strata = {
        "A": (_stratum(0.8), 1_000),
        "B": (_stratum(0.2), 3_000),
    }
    point, _, _ = bootstrap_stratified_rate(strata, resamples=500, seed=1)
    assert point == pytest.approx(0.35)


def test_weights_need_not_be_normalised():
    counts = {"A": (_stratum(0.8), 1), "B": (_stratum(0.2), 3)}
    sizes = {"A": (_stratum(0.8), 1_000), "B": (_stratum(0.2), 3_000)}
    assert bootstrap_stratified_rate(counts, resamples=500, seed=1) == (
        bootstrap_stratified_rate(sizes, resamples=500, seed=1)
    )


def test_the_interval_brackets_the_point_estimate():
    strata = {"A": (_stratum(0.8), 1_000), "B": (_stratum(0.2), 3_000)}
    point, low, high = bootstrap_stratified_rate(strata, resamples=2_000, seed=1)
    assert low <= point <= high


def test_the_seed_makes_it_reproducible():
    # Pages must differ from one another, or every resample is the same draw
    # and the interval is degenerate whatever the seed.
    varied = [(f"p{i}", i, 10) for i in range(11)]
    strata = {"A": (varied, 2), "B": (_stratum(0.3), 1)}
    assert bootstrap_stratified_rate(strata, resamples=500, seed=7) == (
        bootstrap_stratified_rate(strata, resamples=500, seed=7)
    )
    assert bootstrap_stratified_rate(strata, resamples=500, seed=7) != (
        bootstrap_stratified_rate(strata, resamples=500, seed=8)
    )


def test_a_stratum_with_weight_but_no_sampled_pages_is_an_error():
    # Its rate is unobserved, so the weighted total cannot be formed. Treating
    # it as zero would report a measurement that was never taken.
    strata = {"A": (_stratum(0.5), 1_000), "B": ([], 3_000)}
    with pytest.raises(ValueError, match="no sampled"):
        bootstrap_stratified_rate(strata, resamples=100, seed=1)


def test_weights_summing_to_zero_is_an_error():
    with pytest.raises(ValueError, match="no denominator"):
        bootstrap_stratified_rate({"A": (_stratum(0.5), 0)}, resamples=100, seed=1)


def test_no_strata_at_all_is_all_zero():
    assert bootstrap_stratified_rate({}, resamples=10, seed=1) == (0.0, 0.0, 0.0)


def test_an_unobserved_rate_is_nan_and_not_zero():
    assert all(math.isnan(x) for x in bootstrap_rate([]))
