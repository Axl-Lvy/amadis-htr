"""E2's CSVs, from the frozen reach census and the frozen verdicts.

    uv run python eval/correction_results.py
"""

import csv
from pathlib import Path

from amadis_htr.correction import (
    FAMILIES,
    REWRITE_REASON,
    accept_rate_by_page,
    read_reach,
    read_verdicts,
    summarise_confidence,
    summarise_reach,
    summarise_reasons,
    summarise_verdicts,
    write_confidence,
    write_reach,
    write_reasons,
    write_verdicts,
)
from amadis_htr.resample import bootstrap_rate, bootstrap_stratified_rate

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "data/runs/correction"
RESULTS = REPO / "eval/results"

#: Fixed in the pre-registration: 10,000 resamples at 95%.
RESAMPLES = 10_000
SEED = 20260922


def main() -> None:
    reach = summarise_reach(read_reach(RUNS / "REACH.csv"))
    write_reach(reach, RESULTS / "correction-reach.csv")
    whole = next(r for r in reach if r.cohort == "all")
    print(
        f"reach: {whole.pages:,} pages, {whole.correctable:,} correctable lines, "
        f"{whole.lines_with_span:,} with a suspect span "
        f"({whole.lines_with_span / whole.correctable:.1%}), {whole.spans:,} spans"
    )

    verdicts_path = RUNS / "VERDICTS.csv"
    if not verdicts_path.exists():
        print("no VERDICTS.csv yet; the run has not been scored")
        return

    verdicts = read_verdicts(verdicts_path)

    # A partial run may not be scored. `--limit` exists for smoke tests and
    # produces a VERDICTS.csv of the same shape as the real one, so without
    # this check a six-page pilot silently becomes "the result" -- with a
    # family-B row of zeroes presented as a measurement.
    with open(RUNS / "MANIFEST.csv", encoding="utf-8", newline="") as handle:
        manifest = {row["page_id"] for row in csv.DictReader(handle)}
    scored = {v.page_id for v in verdicts}
    missing = manifest - scored
    if missing:
        raise SystemExit(
            f"VERDICTS.csv covers {len(scored)} of the manifest's "
            f"{len(manifest)} pages; {len(missing)} are missing, the first "
            f"being {sorted(missing)[0]}. This is a partial run and scoring it "
            "would report the pilot as the result. Rerun without --limit."
        )

    rows = summarise_verdicts(verdicts)
    write_verdicts(rows, RESULTS / "correction-verdicts.csv")
    write_reasons(summarise_reasons(verdicts), RESULTS / "correction-reasons.csv")
    write_confidence(
        summarise_confidence(verdicts), RESULTS / "correction-confidence.csv"
    )

    # The interval file, and the only place a RATE is computed.
    #
    # The draw is 200 pages per family; the frame is 29.6% family A and 70.4%
    # family B by suspect line. Summing the sample and dividing would weight
    # the corpus by how much of each family was sampled, so the `corpus` rows
    # are frame-weighted and their interval is a stratified bootstrap. The
    # amendment to the pre-registration fixed this before the run was scored.
    weights = {
        r.cohort: float(r.lines_with_span)
        for r in reach
        if r.cohort in FAMILIES
    }
    measures = {
        "accept": lambda v: v.accepted,
        "rewrite": lambda v: v.reason == REWRITE_REASON,
    }
    with open(
        RESULTS / "correction-interval.csv", "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["cohort", "measure", "pages", "point", "low", "high"])
        for measure, hit in measures.items():
            strata = {}
            for family in FAMILIES:
                subset = [v for v in verdicts if v.family == family]
                strata[family] = (
                    accept_rate_by_page(subset, hit=hit),
                    weights[family],
                )
            for family in FAMILIES:
                counts = strata[family][0]
                point, low, high = bootstrap_rate(
                    counts, resamples=RESAMPLES, seed=SEED
                )
                writer.writerow(
                    [family, measure, len(counts), f"{point:.6f}",
                     f"{low:.6f}", f"{high:.6f}"]
                )
            point, low, high = bootstrap_stratified_rate(
                strata, resamples=RESAMPLES, seed=SEED
            )
            writer.writerow(
                ["corpus", measure, sum(len(c) for c, _ in strata.values()),
                 f"{point:.6f}", f"{low:.6f}", f"{high:.6f}"]
            )

    pooled = next(r for r in rows if r.cohort == "all")
    with open(
        RESULTS / "correction-interval.csv", encoding="utf-8", newline=""
    ) as handle:
        intervals = {
            (r["cohort"], r["measure"]): r for r in csv.DictReader(handle)
        }
    corpus = intervals[("corpus", "accept")]
    print(
        f"verdicts: {pooled.offered} lines offered on {pooled.pages} pages, "
        f"{pooled.accepted} accepted in the sample"
    )
    print(
        f"  frame-weighted acceptance {float(corpus['point']):.1%} "
        f"(95% CI {float(corpus['low']):.1%} to {float(corpus['high']):.1%})"
    )
    for family in FAMILIES:
        row = intervals[(family, "accept")]
        print(f"    family {family}: {float(row['point']):.1%}")
    rewrite = intervals[("corpus", "rewrite")]
    print(
        f"  {pooled.rewrites_caught} rewrites caught "
        f"({float(rewrite['point']):.1%} frame-weighted), "
        f"{pooled.protocol_failures} protocol failures"
    )
    print(
        f"  of the accepted, {pooled.changed_spans} spans changed and "
        f"{pooled.accepted_unchanged} lines came back untouched"
    )


if __name__ == "__main__":
    main()
