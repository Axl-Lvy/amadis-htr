"""`eval/results/*.csv` into the `booktabs` tables the report reads.

Rule 1's other half. A macro carries a figure in a sentence; a table carries a
row of them, and both are generated so neither can be typed. Each table is a
bare `tabular`, so the report wraps it in whatever float and caption it wants
and the deck can reuse the same body on a slide.

Each table is written once per report language, from the same rows, with its
labels from `LABELS`. A table whose CSV the evaluation has not produced is
skipped and named.

    uv run python eval/render_tables.py
"""

import csv
from pathlib import Path

from amadis_htr.report_macros import LOCALES, format_value, render_table, write_generated

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "eval/results"
OUT = {
    "en": REPO / "report/generated/tables",
    "fr": REPO / "report/generated/fr/tables",
}

COHORTS = ("workbook", "catalogue")

#: Every word a table prints, per language. Numbers are never here: they come
#: out of `format_value`.
LABELS = {
    "en": {
        "workbook": "batch 1", "catalogue": "batch 2",
        "A": "family A", "B": "family B", "all": "corpus", "sample": "sample",
        "e5": ["Batch", "Extracts", "Right Livre", "Chapter checkable",
               "Right chapter"],
        "e6": ["Family", "Books", "Pages", "Failed", "Hours", "s/page"],
        "e2": ["Family", "Lines tested", "Kept", "Refused: rewrite",
               "Refused: bad reply"],
    },
    "fr": {
        "workbook": "lot 1", "catalogue": "lot 2",
        "A": "famille A", "B": "famille B", "all": "corpus",
        "sample": "échantillon",
        "e5": ["Lot", "Extraits", "Bon Livre", "Chapitre vérifiable",
               "Bon chapitre"],
        "e6": ["Famille", "Livres", "Pages", "Échecs", "Heures", "s/page"],
        "e2": ["Famille", "Lignes testées", "Gardées", "Refus : réécriture",
               "Refus : réponse illisible"],
    },
}


def rows(name: str) -> list[dict[str, str]]:
    with open(RESULTS / name, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def pct(numerator: str, denominator: str, locale: str) -> str:
    """A rate, or an em dash where the denominator is empty.

    0/0 is not 0%. A cohort with no scoreable chapter has no chapter accuracy,
    and printing 0.0% would report a failure the evaluation never observed.
    """
    bottom = float(denominator)
    if not bottom:
        return "---"
    return format_value(str(float(numerator) / bottom), "pct1", locale)


def localisation(locale: str) -> str:
    """E5, one row per cohort, certain band only. Never a pooled row."""
    words = LABELS[locale]
    body = []
    for cohort in COHORTS:
        row = next(r for r in rows(f"localisation-summary-{cohort}.csv")
                   if r["confidence"] == "certain")
        body.append([
            words[cohort],
            format_value(row["total"], "int", locale),
            f'{format_value(row["livre_correct"], "int", locale)} '
            f'({pct(row["livre_correct"], row["total"], locale)})',
            format_value(row["chapter_scoreable"], "int", locale),
            f'{format_value(row["chapter_correct"], "int", locale)} '
            f'({pct(row["chapter_correct"], row["chapter_scoreable"], locale)})',
        ])
    return render_table(headers=words["e5"], aligns="lrrrr", rows=body)


def throughput(locale: str) -> str:
    """E6, per family and pooled."""
    words = LABELS[locale]
    body = [
        [
            words[r["cohort"]],
            format_value(r["books"], "int", locale),
            format_value(r["pages"], "int", locale),
            format_value(r["failed"], "int", locale),
            format_value(r["seconds"], "hours2", locale),
            format_value(r["seconds_per_page"], "num3", locale),
        ]
        for r in rows("throughput.csv")
    ]
    return render_table(headers=words["e6"], aligns="lrrrrr", rows=body)


def correction(locale: str) -> str:
    """E2, per family and the sample total.

    The total row carries **counts only**. The draw is equal per family and the
    frame is not, so accepted/offered over the pooled sample weights family A
    at more than twice its share of the corpus. The amendment to the
    pre-registration says no rate is computed from that row, and this is where
    it would otherwise have been: the two families differ by more than three
    points, so the naive pooled rate and the frame-weighted one are not the
    same number. The weighted estimate is a macro, read from the interval file.
    """
    words = LABELS[locale]
    rows_ = {r["cohort"]: r for r in rows("correction-verdicts.csv")}
    body = []
    for cohort, label in (("A", "A"), ("B", "B"), ("all", "sample")):
        r = rows_[cohort]
        accepted = format_value(r["accepted"], "int", locale)
        if cohort != "all":
            accepted += f' ({pct(r["accepted"], r["offered"], locale)})'
        body.append([
            words[label],
            format_value(r["offered"], "int", locale),
            accepted,
            format_value(r["rewrites_caught"], "int", locale),
            format_value(r["protocol_failures"], "int", locale),
        ])
    return render_table(headers=words["e2"], aligns="lrrrr", rows=body)


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
        for locale in LOCALES:
            path = OUT[locale] / f"{name}.tex"
            write_generated(build(locale), path)
            print(f"  {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
