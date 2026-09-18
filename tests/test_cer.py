import math

from amadis_htr.cer import (
    PageScore,
    aggregate,
    flatten,
    score_page,
    substitution_counts,
)


def test_flatten_collapses_whitespace_runs():
    assert flatten("a  b\n c\t\td ") == "a b c d"


def test_identical_text_scores_zero():
    s = score_page("p1", "le roy Lisuart", "le roy Lisuart")
    assert s.cer == 0.0
    assert s.wer == 0.0
    assert s.char_edits == 0


def test_one_substituted_character():
    s = score_page("p1", "abcd", "abxd")
    assert s.ref_chars == 4
    assert s.char_edits == 1
    assert math.isclose(s.cer, 0.25)


def test_whitespace_counts_as_a_character():
    # A lost word boundary is one deletion, not a free pass.
    s = score_page("p1", "deux mots", "deuxmots")
    assert s.char_edits == 1
    assert s.ref_chars == 9


def test_word_error_rate():
    s = score_page("p1", "le roy Lisuart livra", "le roi Lisuart livra")
    assert s.ref_words == 4
    assert s.word_edits == 1
    assert math.isclose(s.wer, 0.25)


def test_folded_scoring_forgives_convention_only():
    raw = score_page("p1", "auoit", "avoit")
    folded = score_page("p1", "auoit", "avoit", folded=True)
    assert raw.char_edits == 1
    assert folded.char_edits == 0


def test_folded_scoring_still_counts_real_errors():
    folded = score_page("p1", "nostre", "notre", folded=True)
    assert folded.char_edits == 1


def test_aggregate_is_character_weighted_not_page_averaged():
    # A short perfect page must not offset a long bad one.
    long_bad = PageScore("a", 0.5, 0.5, 100, 20, 50, 10)
    short_good = PageScore("b", 0.0, 0.0, 10, 2, 0, 0)
    cer, wer = aggregate([long_bad, short_good])
    assert math.isclose(cer, 50 / 110)
    assert math.isclose(wer, 10 / 22)


def test_aggregate_of_nothing_is_zero():
    assert aggregate([]) == (0.0, 0.0)


def test_substitution_counts_reports_the_confused_pair():
    counts = substitution_counts("fecourir", "secourir")
    assert counts[("f", "s")] == 1


def test_empty_reference_and_hypothesis_score_zero():
    s = score_page("p1", "", "")
    assert (s.cer, s.wer, s.ref_chars, s.char_edits) == (0.0, 0.0, 0, 0)


def test_an_empty_reference_with_text_yields_no_rate():
    # Measured: jiwer counts 3 insertions and 0 hits, so ref_chars is 0 and no
    # rate is definable. Recorded here because excluded lines produce empty
    # reference segments and this must not raise or divide by zero.
    s = score_page("p1", "", "abc")
    assert s.ref_chars == 0
    assert s.cer == 0.0
    assert s.char_edits == 3


def test_an_empty_hypothesis_scores_a_total_loss():
    s = score_page("p1", "abc", "")
    assert s.ref_chars == 3
    assert s.char_edits == 3
    assert s.cer == 1.0
