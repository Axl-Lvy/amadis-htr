import math

from amadis_htr.ground_truth import Reference
from amadis_htr.localisation import (
    Prediction,
    read_ground_truth,
    read_predictions,
    summarise,
    sweep,
    write_sweep,
)


def _refs() -> dict[int, Reference]:
    return {
        1: Reference(1, 4, 12, "certain", "Livre 4, chap 12"),
        2: Reference(2, 4, 13, "certain", "Livre 4, chap 13"),
        3: Reference(3, 8, None, "certain", "Livre 8"),
        4: Reference(4, 2, 22, "conjecture", "[Livre 2, chap 22]"),
        5: Reference(5, None, None, "none", ""),
    }


def _preds() -> dict[int, Prediction]:
    return {
        1: Prediction(1, 4, 12, 0.95),   # right livre, right chapter
        2: Prediction(2, 4, 99, 0.90),   # right livre, wrong chapter
        3: Prediction(3, 9, 1, 0.70),    # wrong livre
        4: Prediction(4, 2, 22, 0.85),   # a conjecture, scored separately
        5: Prediction(5, 1, 1, 0.60),    # no reference, unscoreable
    }


def test_summary_is_broken_down_by_confidence():
    rows = {s.confidence: s for s in summarise(_refs(), _preds())}
    assert set(rows) == {"certain", "conjecture", "uncertain", "none"}


def test_certain_rows_score_livre_and_chapter_separately():
    certain = {s.confidence: s for s in summarise(_refs(), _preds())}["certain"]
    assert certain.total == 3
    assert certain.located == 3
    assert certain.livre_correct == 2          # pieces 1 and 2
    assert certain.chapter_scoreable == 2      # piece 3 has no reference chapter
    assert certain.chapter_correct == 1        # only piece 1


def test_rows_with_no_reference_are_counted_but_never_scored():
    none = {s.confidence: s for s in summarise(_refs(), _preds())}["none"]
    assert none.total == 1
    assert none.livre_correct == 0
    assert none.chapter_scoreable == 0


def test_a_missing_prediction_counts_as_not_located():
    preds = _preds()
    del preds[1]
    certain = {s.confidence: s for s in summarise(_refs(), preds)}["certain"]
    assert certain.total == 3
    assert certain.located == 2
    assert certain.livre_correct == 1


def test_a_prediction_with_no_livre_is_not_located():
    preds = _preds()
    preds[1] = Prediction(1, None, None, 0.0)
    certain = {s.confidence: s for s in summarise(_refs(), preds)}["certain"]
    assert certain.located == 2


def test_sweep_trades_precision_against_coverage():
    rows = {r.threshold: r for r in sweep(_refs(), _preds(), [0.0, 0.8, 0.92])}

    at_zero = rows[0.0]
    assert at_zero.accepted == 3           # the three certain pieces
    assert at_zero.correct == 2
    assert math.isclose(at_zero.precision, 2 / 3)
    assert math.isclose(at_zero.coverage, 1.0)

    at_high = rows[0.92]
    assert at_high.accepted == 1           # only piece 1 scores above 0.92
    assert at_high.correct == 1
    assert math.isclose(at_high.precision, 1.0)
    assert math.isclose(at_high.coverage, 1 / 3)


def test_sweep_precision_is_zero_when_nothing_is_accepted():
    row = sweep(_refs(), _preds(), [1.1])[0]
    assert row.accepted == 0
    assert row.precision == 0.0
    assert row.coverage == 0.0


def test_reading_the_real_ground_truth_file():
    refs = read_ground_truth("data/localisation/ground-truth.csv")
    assert len(refs) == 457
    assert refs[1].livre == 1
    assert refs[1].chapter == 9
    assert refs[1].confidence == "certain"


def test_reading_predictions(tmp_path):
    path = tmp_path / "alignments.csv"
    path.write_text(
        "piece,livre,chapter,start,end,score\n"
        "1,4,12,100,900,0.95\n"
        "2,,,,,0.0\n",
        encoding="utf-8",
    )
    preds = read_predictions(path)
    assert preds[1] == Prediction(1, 4, 12, 0.95)
    assert preds[2] == Prediction(2, None, None, 0.0)


def test_write_sweep_has_a_header(tmp_path):
    out = tmp_path / "sweep.csv"
    write_sweep(sweep(_refs(), _preds(), [0.0]), out)
    assert out.read_text(encoding="utf-8").splitlines()[0] == (
        "threshold,accepted,correct,precision,coverage"
    )


def test_writers_create_their_own_output_directory(tmp_path):
    # No .gitkeep placeholder holds eval/results open, so a writer that assumed
    # its directory existed would fail on a clean checkout.
    out = tmp_path / "results" / "nested" / "sweep.csv"
    write_sweep(sweep(_refs(), _preds(), [0.0]), out)
    assert out.exists()
