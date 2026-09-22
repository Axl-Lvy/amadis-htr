"""`eval/results/*.csv` into the `booktabs` tables the report reads.

Rule 1's other half. A macro carries a figure in a sentence; a table carries a
row of them, and both are generated so neither can be typed. Each table is a
bare `tabular`, so the report wraps it in whatever float and caption it wants
and the deck can reuse the same body on a slide.

A table whose CSV the evaluation has not produced is skipped and named.

    uv run python eval/render_tables.py
"""

import csv
from pathlib import Path

from amadis_htr.report_macros import format_value, render_table, write_generated

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "eval/results"
OUT = REPO / "report/generated/tables"

COHORTS = ("workbook", "catalogue")


def rows(name: str) -> list[dict[str, str]]:
    with open(RESULTS / name, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def pct(numerator: str, denominator: str) -> str:
    """A rate, or an em dash where the denominator is empty.

    0/0 is not 0%. A cohort with no scoreable chapter has no chapter accuracy,
    and printing 0.0% would report a failure the evaluation never observed.
    """
    bottom = float(denominator)
    if not bottom:
        return "---"
    return format_value(str(float(numerator) / bottom), "pct1")


def localisation() -> str:
    """E5, one row per cohort, certain band only. Never a pooled row."""
    body = []
    for cohort in COHORTS:
        row = next(r for r in rows(f"localisation-summary-{cohort}.csv")
                   if r["confidence"] == "certain")
        body.append([
            cohort,
            format_value(row["total"], "int"),
            f'{format_value(row["livre_correct"], "int")} '
            f'({pct(row["livre_correct"], row["total"])})',
            format_value(row["chapter_scoreable"], "int"),
            f'{format_value(row["chapter_correct"], "int")} '
            f'({pct(row["chapter_correct"], row["chapter_scoreable"])})',
        ])
    return render_table(
        headers=["Cohort", "Pieces", "Livre correct", "Chapter scoreable",
                 "Chapter correct"],
        aligns="lrrrr",
        rows=body,
    )


def throughput() -> str:
    """E6, per family and pooled."""
    body = [
        [
            {"A": "family A", "B": "family B", "all": "corpus"}[r["cohort"]],
            format_value(r["books"], "int"),
            format_value(r["pages"], "int"),
            format_value(r["failed"], "int"),
            format_value(r["seconds"], "hours2"),
            format_value(r["seconds_per_page"], "num3"),
        ]
        for r in rows("throughput.csv")
    ]
    return render_table(
        headers=["Cohort", "Books", "Pages", "Failed", "Hours", "s/page"],
        aligns="lrrrrr",
        rows=body,
    )


def correction() -> str:
    """E2, per family and the sample total.

    The total row carries **counts only**. The draw is equal per family and the
    frame is not, so accepted/offered over the pooled sample weights family A
    at more than twice its share of the corpus. The amendment to the
    pre-registration says no rate is computed from that row, and this is where
    it would otherwise have been: the two families differ by more than three
    points, so the naive pooled rate and the frame-weighted one are not the
    same number. The weighted estimate is a macro, read from the interval file.
    """
    rows_ = {r["cohort"]: r for r in rows("correction-verdicts.csv")}
    body = []
    for cohort, label in (("A", "family A"), ("B", "family B"), ("all", "sample")):
        r = rows_[cohort]
        accepted = format_value(r["accepted"], "int")
        if cohort != "all":
            accepted += f' ({pct(r["accepted"], r["offered"])})'
        body.append([
            label,
            format_value(r["offered"], "int"),
            accepted,
            format_value(r["rewrites_caught"], "int"),
            format_value(r["protocol_failures"], "int"),
            format_value(r["on_find_fallback"], "int"),
        ])
    return render_table(
        headers=["Cohort", "Lines offered", "Accepted", "Rewrites caught",
                 "Protocol failures", "On find fallback"],
        aligns="lrrrrr",
        rows=body,
    )


TABLES = (
    ("e5-localisation", localisation,
     ("localisation-summary-workbook.csv", "localisation-summary-catalogue.csv")),
    ("e6-throughput", throughput, ("throughput.csv",)),
    ("e2-correction", correction, ("correction-verdicts.csv",)),
)


def main() -> None:
    for name, build, needs in TABLES:
        if not all((RESULTS / n).exists() for n in needs):
            print(f"  skipped {name}: {', '.join(needs)} not measured yet")
            continue
        write_generated(build(), OUT / f"{name}.tex")
        print(f"  {(OUT / f'{name}.tex').relative_to(REPO)}")


if __name__ == "__main__":
    main()
