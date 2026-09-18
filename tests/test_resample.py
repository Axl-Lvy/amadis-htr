import math

from amadis_htr.cer import PageScore
from amadis_htr.resample import bootstrap_cer


def _page(page_id: str, ref_chars: int, char_edits: int) -> PageScore:
    return PageScore(
        page_id=page_id,
        cer=char_edits / ref_chars,
        wer=0.0,
        ref_chars=ref_chars,
        ref_words=ref_chars // 5,
        char_edits=char_edits,
        word_edits=0,
    )


def test_point_estimate_matches_the_weighted_aggregate():
    pages = [_page("a", 100, 5), _page("b", 200, 5)]
    point, _, _ = bootstrap_cer(pages, resamples=200, seed=1)
    assert math.isclose(point, 10 / 300)


def test_interval_brackets_the_point_estimate():
    pages = [_page(str(i), 100, i) for i in range(20)]
    point, low, high = bootstrap_cer(pages, resamples=2000, seed=1)
    assert low <= point <= high


def test_identical_pages_give_a_degenerate_interval():
    pages = [_page(str(i), 100, 5) for i in range(10)]
    point, low, high = bootstrap_cer(pages, resamples=500, seed=1)
    assert math.isclose(low, point)
    assert math.isclose(high, point)


def test_seed_makes_it_reproducible():
    pages = [_page(str(i), 100, i) for i in range(20)]
    assert bootstrap_cer(pages, resamples=500, seed=7) == bootstrap_cer(
        pages, resamples=500, seed=7
    )


def test_different_seeds_differ():
    pages = [_page(str(i), 100, i) for i in range(20)]
    assert bootstrap_cer(pages, resamples=500, seed=7) != bootstrap_cer(
        pages, resamples=500, seed=8
    )


def test_empty_input_is_all_zero():
    assert bootstrap_cer([], resamples=10, seed=1) == (0.0, 0.0, 0.0)
