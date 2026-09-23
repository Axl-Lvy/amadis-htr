"""E5's four CSVs, from the frozen matcher run and the editor's reference.

Both inputs are committed, so this runs anywhere Python does: no database, no
network, no big PC. That is the point of freezing `data/runs/`. The outputs are
committed too, and rerunning this on an unchanged input rewrites them
identically, which is what `tests/test_localisation.py` asserts.

    uv run python eval/localisation_results.py
"""

from pathlib import Path

from amadis_htr.localisation import (
    SWEEP_THRESHOLDS,
    chapter_errors,
    read_ground_truth,
    read_predictions_by_cohort,
    references_for,
    summarise,
    sweep,
    write_chapter_errors,
    write_summary,
    write_sweep,
)

REPO = Path(__file__).resolve().parent.parent
ALIGNMENTS = REPO / "data/runs/matcher/alignments.csv"
GROUND_TRUTH = REPO / "data/localisation/ground-truth.csv"
RESULTS = REPO / "eval/results"


def main() -> None:
    references = read_ground_truth(GROUND_TRUTH)
    by_cohort = read_predictions_by_cohort(ALIGNMENTS)

    errors = []
    for cohort, predictions in sorted(by_cohort.items()):
        scoped = references_for(references, predictions)
        errors.append(chapter_errors(cohort, scoped, predictions))
        rows = summarise(scoped, predictions)
        write_summary(rows, RESULTS / f"localisation-summary-{cohort}.csv")
        write_sweep(
            sweep(scoped, predictions, SWEEP_THRESHOLDS),
            RESULTS / f"localisation-sweep-{cohort}.csv",
        )
        certain = next(r for r in rows if r.confidence == "certain")
        print(
            f"{cohort}: {certain.total} certain pieces, "
            f"{certain.livre_correct} Livre correct, "
            f"{certain.chapter_correct} of {certain.chapter_scoreable} chapter "
            f"correct, {certain.chapter_unavailable} with no printed number"
        )

    # Pooled only here, and only to describe the misses: no rate in the report
    # is computed over both batches.
    everything = {p: pred for preds in by_cohort.values() for p, pred in preds.items()}
    errors.append(
        chapter_errors("all", references_for(references, everything), everything)
    )
    write_chapter_errors(errors, RESULTS / "localisation-chapter-errors.csv")
    pooled = errors[-1]
    print(
        f"chapter misses in the right Livre: {pooled.numeral_close + pooled.other}, "
        f"of which {pooled.numeral_close} are within {2} roman letters"
    )


if __name__ == "__main__":
    main()
