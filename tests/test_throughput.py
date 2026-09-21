import json
from pathlib import Path

from amadis_htr.throughput import (
    Run,
    Structure,
    read_runs,
    read_structures,
    summarise_structure,
    summarise_throughput,
    write_structure,
    write_throughput,
)

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "data/runs/ocr"


def _run(book: int, family: str, pages: int, seconds: float, failed: int = 0) -> Run:
    return Run(
        book=book,
        family=family,
        pages=pages,
        failed=failed,
        seconds=seconds,
        passages=0,
        unresolved_ambiguous=0,
    )


def _structure(book: int, family: str, toc: int | None, matched: int = 0,
               missing: int = 0, spurious: int = 0) -> Structure:
    return Structure(
        book=book, family=family, pages=10, body=0, header=0, footer=0,
        title=0, empty_pages=0, anomalies=0, toc_chapters=toc,
        matched=matched if toc is not None else None,
        missing=missing if toc is not None else None,
        spurious=spurious if toc is not None else None,
        unscorable=0 if toc is not None else None,
    )


def test_all_twenty_four_books_are_frozen():
    runs = read_runs(RUNS)
    assert len(runs) == 24
    assert [r.book for r in runs] == list(range(1, 25))


def test_the_frozen_records_carry_no_absolute_path():
    # The records were vendored from one person's machine. Their counts are the
    # method; where that machine keeps its corpus and that the model came off a
    # private home-lab checkout are not.
    for path in sorted(RUNS.rglob("*.json")):
        assert "/home" not in path.read_text(encoding="utf-8"), path


def test_one_model_on_one_device_at_one_width_which_is_what_lets_pooling_work():
    # Throughput pools across families. That is only legitimate while every
    # book was run the same way, so the condition is asserted rather than
    # assumed.
    configs = set()
    for directory in sorted(RUNS.iterdir()):
        if not directory.is_dir():
            continue
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        configs.add((run["model"], run["device"], run["workingWidth"], run["workers"]))
    assert configs == {("amadis-ft.mlmodel", "gpu", 2200, 16)}


def test_the_corpus_figures_are_what_the_records_say():
    rows = summarise_throughput(read_runs(RUNS))
    whole = next(r for r in rows if r.cohort == "all")
    assert whole.books == 24
    assert whole.pages == 14111
    assert whole.failed == 0
    assert round(whole.seconds_per_page, 3) == 1.441
    assert round(whole.seconds / 3600, 2) == 5.65


def test_the_families_partition_the_corpus():
    rows = {r.cohort: r for r in summarise_throughput(read_runs(RUNS))}
    assert rows["A"].pages + rows["B"].pages == rows["all"].pages
    assert rows["A"].books + rows["B"].books == rows["all"].books


def test_family_b_has_no_structural_row_because_it_prints_no_contents():
    # Books 13 to 24 carry no printed table of contents, so their
    # calibration.json has no match block at all. A zero row would say the
    # harness looked and found nothing, and an `all` row would be family A's
    # figure wearing the whole corpus's denominator.
    structures = read_structures(RUNS)
    assert all(s.toc_chapters is None for s in structures if s.family == "B")
    rows = summarise_structure(structures)
    assert [r.cohort for r in rows] == ["A"]


def test_recall_and_precision_use_the_denominators_the_harness_used():
    # recall is matched over the printed chapters, precision is matched over
    # what the run proposed. Checked against all twelve per-book figures the
    # harness wrote for itself.
    rows = summarise_structure(read_structures(RUNS))
    row = rows[0]
    assert row.matched + row.missing == row.toc_chapters
    assert row.recall == row.matched / row.toc_chapters
    assert row.precision == row.matched / (row.matched + row.spurious)


def test_a_book_with_no_pages_does_not_divide_by_zero():
    rows = summarise_throughput([_run(1, "A", 0, 0.0)])
    assert next(r for r in rows if r.cohort == "A").seconds_per_page == 0.0


def test_the_committed_results_regenerate_from_the_frozen_records(tmp_path):
    throughput = tmp_path / "throughput.csv"
    structure = tmp_path / "structure.csv"
    write_throughput(summarise_throughput(read_runs(RUNS)), throughput)
    write_structure(summarise_structure(read_structures(RUNS)), structure)
    for produced in (throughput, structure):
        committed = REPO / "eval/results" / produced.name
        # read_bytes, not read_text: text mode normalises newlines, so a
        # committed copy whose line endings were rewritten on checkout would
        # compare equal while `git diff` after a rerun showed every row changed.
        assert produced.read_bytes() == committed.read_bytes(), (
            f"{produced.name} does not match the committed copy"
        )


def test_a_family_with_nothing_to_calibrate_against_yields_no_row():
    rows = summarise_structure([_structure(13, "B", None), _structure(14, "B", None)])
    assert rows == []
