import math
from pathlib import Path

from amadis_htr.ground_truth import Reference
from amadis_htr.localisation import (
    SWEEP_THRESHOLDS,
    Prediction,
    read_ground_truth,
    read_predictions,
    read_predictions_by_cohort,
    references_for,
    summarise,
    sweep,
    write_summary,
    write_sweep,
)

REPO = Path(__file__).resolve().parent.parent


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


def test_a_prediction_with_no_printed_chapter_is_set_aside_not_failed():
    preds = _preds()
    preds[2] = Prediction(2, 4, None, 0.90)
    certain = {s.confidence: s for s in summarise(_refs(), preds)}["certain"]
    assert certain.chapter_scoreable == 1        # only piece 1 remains comparable
    assert certain.chapter_correct == 1
    assert certain.chapter_unavailable == 1      # piece 2 has no printed number


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


def test_the_sweep_thresholds_are_the_numbers_they_are_printed_as():
    # Adding 0.01 sixty times reaches 0.8600000000000001, and a piece scoring
    # exactly 0.86 then falls on the other side of `score < threshold`. That is
    # one accepted piece in the catalogue cohort, so the thresholds are built by
    # dividing integers instead.
    assert len(SWEEP_THRESHOLDS) == 61
    assert SWEEP_THRESHOLDS[0] == 0.40 and SWEEP_THRESHOLDS[-1] == 1.00
    assert SWEEP_THRESHOLDS[46] == 0.86
    accumulated = [0.400 + 0.010 * i for i in range(61)]
    assert accumulated[46] != 0.86


def test_the_two_cohorts_are_read_apart():
    by_cohort = read_predictions_by_cohort(REPO / "data/runs/matcher/alignments.csv")
    assert set(by_cohort) == {"catalogue", "workbook"}
    # The batches are disjoint: no piece was imported twice.
    assert not set(by_cohort["catalogue"]) & set(by_cohort["workbook"])


def test_a_cohort_is_scored_only_on_the_pieces_it_holds():
    # Keeping the other cohort's references in the denominator would count
    # every piece this batch never imported as one it failed to locate.
    references = read_ground_truth(REPO / "data/localisation/ground-truth.csv")
    by_cohort = read_predictions_by_cohort(REPO / "data/runs/matcher/alignments.csv")
    scoped = references_for(references, by_cohort["workbook"])
    assert set(scoped) <= set(by_cohort["workbook"])
    assert len(scoped) < len(references)


def test_the_committed_results_regenerate_from_the_committed_inputs(tmp_path):
    # data/runs/ is frozen so the evaluation reruns on any machine with Python.
    # That only means something while a rerun reproduces what is committed, so
    # this is the check that eval/results was not hand-edited and that the
    # matcher output behind it is the one the numbers came from.
    references = read_ground_truth(REPO / "data/localisation/ground-truth.csv")
    by_cohort = read_predictions_by_cohort(REPO / "data/runs/matcher/alignments.csv")
    for cohort, predictions in by_cohort.items():
        scoped = references_for(references, predictions)
        summary = tmp_path / f"localisation-summary-{cohort}.csv"
        sweep_out = tmp_path / f"localisation-sweep-{cohort}.csv"
        write_summary(summarise(scoped, predictions), summary)
        write_sweep(sweep(scoped, predictions, SWEEP_THRESHOLDS), sweep_out)
        for produced in (summary, sweep_out):
            committed = REPO / "eval/results" / produced.name
            assert produced.read_text(encoding="utf-8") == committed.read_text(
                encoding="utf-8"
            ), f"{produced.name} does not match the committed copy"
