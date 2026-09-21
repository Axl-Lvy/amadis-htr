from pathlib import Path

import pytest

from amadis_htr.corpus import (
    Piece,
    read_pieces,
    read_training_pages,
    summarise_corpus,
    summarise_training,
    write_corpus,
    write_training,
)
from amadis_htr.ground_truth import Reference
from amadis_htr.localisation import read_ground_truth
from amadis_htr.report_macros import COHORTS

REPO = Path(__file__).resolve().parent.parent
REFERENCE = REPO / "data/localisation/ground-truth.csv"
ALIGNMENTS = REPO / "data/runs/matcher/alignments.csv"
TRAINING = REPO / "data/gold/splits/training-pages.csv"


def _reference(piece: int, confidence: str = "certain", livre: int | None = 1):
    return Reference(
        piece=piece, livre=livre, chapter=None, confidence=confidence, raw=""
    )


def _pieces() -> list[Piece]:
    return read_pieces(read_ground_truth(REFERENCE), ALIGNMENTS)


def test_the_reference_is_the_frame_and_every_piece_survives_the_join():
    pieces = _pieces()
    assert len(pieces) == 457
    assert [p.piece for p in pieces] == sorted(p.piece for p in pieces)


def test_an_alignment_outside_the_reference_is_an_export_fault(tmp_path):
    # A piece the matcher placed but the editor never catalogued cannot be a
    # corpus fact, so it stops the census rather than enlarging it.
    alignments = tmp_path / "alignments.csv"
    alignments.write_text(
        "piece,cohort,passage_id,livre,chapter,start,end,score\n"
        "1,workbook,x,1,1,0,100,0.9\n"
        "999,workbook,y,1,1,0,100,0.9\n",
        encoding="utf-8",
    )
    with pytest.raises(KeyError, match="not in the reference"):
        read_pieces({1: _reference(1)}, alignments)


def test_the_cohorts_partition_the_aligned_pieces_and_not_the_reference():
    # 457 catalogued, 453 placed. The `all` row is deliberately wider than the
    # two cohort rows together, and `unaligned` is the whole of the difference.
    rows = {r.cohort: r for r in summarise_corpus(_pieces(), COHORTS)}
    assert rows["all"].pieces == 457
    assert rows["all"].aligned == 453
    assert rows["all"].unaligned == 4
    assert rows["catalogue"].aligned + rows["workbook"].aligned == rows["all"].aligned
    for cohort in COHORTS:
        assert rows[cohort].pieces == rows[cohort].aligned
        assert rows[cohort].unaligned == 0


def test_the_confidence_bands_account_for_every_catalogued_piece():
    row = next(r for r in summarise_corpus(_pieces(), COHORTS) if r.cohort == "all")
    assert row.certain + row.conjecture + row.uncertain + row.none == row.pieces
    assert (row.certain, row.conjecture, row.uncertain, row.none) == (422, 4, 10, 21)


def test_an_unplaced_piece_has_no_extract_length_rather_than_a_zero_one():
    # A zero would say the matcher placed the piece and found it empty.
    unplaced = Piece(1, "certain", 1, None, None, None)
    assert unplaced.chars is None
    rows = summarise_corpus([unplaced], COHORTS)
    whole = next(r for r in rows if r.cohort == "all")
    assert whole.aligned == 0
    assert whole.chars_mean == 0.0


def test_a_cohort_the_matcher_stopped_emitting_still_gets_a_row():
    # Passed in rather than discovered, so the absence is visible in the table.
    rows = summarise_corpus([], ("catalogue", "workbook"))
    assert [r.cohort for r in rows] == ["catalogue", "workbook", "all"]


def test_the_extract_spans_are_the_offsets_the_matcher_exported():
    rows = {r.cohort: r for r in summarise_corpus(_pieces(), COHORTS)}
    whole = rows["all"]
    assert whole.chars_min == 189
    assert whole.chars_max == 5756
    # The two cohorts excerpt differently, which is why section 3 reports them
    # apart: the workbook's pieces run about a third longer.
    assert rows["workbook"].chars_mean > rows["catalogue"].chars_mean


def test_the_training_pages_are_one_collection():
    # Section 3 claims the fine-tune saw Trésor T.1 and nothing else. The page
    # id's first field is the Transkribus collection, so the claim is checkable
    # rather than quoted from a README.
    rows = {r.split: r for r in summarise_training(read_training_pages(TRAINING))}
    assert rows["all"].pages == 487
    assert rows["all"].collections == 1
    assert rows["train"].pages + rows["val"].pages == rows["all"].pages
    assert rows["val"].pages == 48


def test_the_committed_results_regenerate_from_the_committed_inputs(tmp_path):
    corpus = tmp_path / "corpus.csv"
    training = tmp_path / "training.csv"
    write_corpus(summarise_corpus(_pieces(), COHORTS), corpus)
    write_training(summarise_training(read_training_pages(TRAINING)), training)
    for produced in (corpus, training):
        committed = REPO / "eval/results" / produced.name
        # read_bytes, not read_text: text mode normalises newlines, so a
        # committed copy whose line endings were rewritten on checkout would
        # compare equal while `git diff` after a rerun showed every row changed.
        assert produced.read_bytes() == committed.read_bytes(), (
            f"{produced.name} does not match the committed copy"
        )
