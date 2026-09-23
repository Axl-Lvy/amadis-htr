"""Every figure in the report, from `eval/results/*.csv`.

Three figures and no more. A bar chart of two bars says what a sentence says,
and the report is ten pages: `corpus-extracts` and `e2-reasons` were dropped on
2026-09-22 because their numbers are already in the prose beside them. The
CSVs they read are still written and still checked.

Rule 1 covers figures as well as numbers: a plot is a reported figure, so it is
drawn from the committed results and never from a screenshot or a hand-made
table. A figure whose CSV the evaluation has not produced is skipped and named,
rather than drawn from nothing.

    uv run python figures/make_figures.py
"""

import csv
from pathlib import Path

import matplotlib.pyplot as plt

from figures.style import (
    BLUE,
    FAMILY,
    GREY,
    LIGHT,
    RED,
    RESULTS,
    TEAL,
    localise_ticks,
    save,
    setup,
)

#: Every word a figure prints, per report language.
LABELS = {
    "en": {
        "workbook": "workbook",
        "catalogue": "catalogue",
        "operating point": "operating point",
        "precision": "precision (%)",
        "coverage": "coverage (%)",
        "threshold": "accept threshold",
        "corpus mean": "corpus mean",
        "family": "family {}",
        "seconds per page": "seconds per page",
        "book": "book",
        "accepted": "accepted ({})",
        "rejected": "rejected ({})",
        "confidence": "lowest character confidence on the line",
        "density": "density",
    },
    "fr": {
        "workbook": "classeur",
        "catalogue": "catalogue",
        "operating point": "seuil retenu",
        "precision": "précision (%)",
        "coverage": "couverture (%)",
        "threshold": "seuil d'acceptation",
        "corpus mean": "moyenne",
        "family": "famille {}",
        "seconds per page": "secondes par page",
        "book": "livre",
        "accepted": "acceptées ({})",
        "rejected": "refusées ({})",
        "confidence": "confiance minimale d'un caractère de la ligne",
        "density": "densité",
    },
}


def rows(name: str) -> list[dict[str, str]]:
    with open(RESULTS / name, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def have(*names: str) -> bool:
    return all((RESULTS / name).exists() for name in names)


def localisation_sweep(locale: str) -> None:
    """E5: precision and coverage against the accept threshold, per cohort.

    The sweep is E5's real result. A single threshold observed once is not a
    decision boundary; the curve is, and it shows what coverage costs.

    Points where nothing is accepted are dropped rather than drawn. Precision
    over an empty accept set is 0/0, and the CSV writes it as 0.0; plotting
    that would show the precision collapsing at a high threshold when what
    collapsed is the denominator.
    """
    words = LABELS[locale]
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(5.2, 2.5), sharex=True, height_ratios=[1, 1]
    )
    for cohort, colour in (("workbook", BLUE), ("catalogue", RED)):
        data = [r for r in rows(f"localisation-sweep-{cohort}.csv")
                if int(r["accepted"]) > 0]
        x = [float(r["threshold"]) for r in data]
        top.plot(x, [float(r["precision"]) * 100 for r in data], color=colour,
                 label=words[cohort])
        bottom.plot(x, [float(r["coverage"]) * 100 for r in data], color=colour)

    # MIN_SCORE, the threshold the system actually runs at.
    for axis in (top, bottom):
        axis.axvline(0.808, color=GREY, lw=0.8, ls=":", zorder=0)
    top.text(0.812, 98.35, words["operating point"], color=GREY, fontsize=7,
             va="bottom")

    top.set_ylabel(words["precision"])
    top.set_ylim(98.2, 100.3)
    top.legend(loc="lower left")
    bottom.set_ylabel(words["coverage"])
    bottom.set_xlabel(words["threshold"])
    bottom.set_ylim(-3, 105)
    for axis in (top, bottom):
        axis.margins(x=0.01)
    localise_ticks(fig, locale)
    save(fig, "e5-sweep", locale)


def throughput_by_book(locale: str) -> None:
    """E6: seconds per page, one bar per book, coloured by type family.

    The pooled mean answers how fast; this answers how evenly, and the spread
    across 24 books is what a single mean hides.
    """
    words = LABELS[locale]
    data = rows("throughput-by-book.csv")
    pooled = {r["cohort"]: r for r in rows("throughput.csv")}
    fig, axis = plt.subplots(figsize=(5.2, 1.8))
    axis.bar(
        [int(r["book"]) for r in data],
        [float(r["seconds_per_page"]) for r in data],
        color=[FAMILY[r["family"]] for r in data],
        width=0.72,
    )
    axis.axhline(
        float(pooled["all"]["seconds_per_page"]), color=RED, lw=0.9, ls="--", zorder=3
    )
    axis.text(
        24.6, float(pooled["all"]["seconds_per_page"]), words["corpus mean"],
        color=RED, fontsize=7, va="bottom",
    )
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=FAMILY[f], label=words["family"].format(f))
        for f in ("A", "B")
    ]
    axis.legend(handles=handles, loc="upper left", ncols=2)
    axis.set_ylabel(words["seconds per page"])
    axis.set_xlabel(words["book"])
    axis.set_xticks([1, 6, 12, 18, 24])
    axis.set_xlim(0.2, 28.5)
    axis.set_ylim(0, 2.45)
    localise_ticks(fig, locale)
    save(fig, "e6-throughput", locale)


def correction_confidence(locale: str) -> None:
    """E2: the recogniser's confidence on accepted against rejected lines."""
    import csv as _csv

    path = Path(RESULTS).parent.parent / "data/runs/correction/VERDICTS.csv"
    if not path.exists():
        return
    with open(path, encoding="utf-8", newline="") as handle:
        verdicts = list(_csv.DictReader(handle))
    accepted = [float(v["min_conf"]) for v in verdicts if v["accepted"] == "1"]
    rejected = [float(v["min_conf"]) for v in verdicts if v["accepted"] != "1"]
    if not rejected:
        return
    words = LABELS[locale]
    fig, axis = plt.subplots(figsize=(5.2, 1.7))
    bins = [i / 20 for i in range(0, 13)]
    axis.hist(
        [accepted, rejected], bins=bins, color=[BLUE, RED], density=True,
        label=[words["accepted"].format(len(accepted)),
               words["rejected"].format(len(rejected))],
    )
    axis.set_xlabel(words["confidence"])
    axis.set_ylabel(words["density"])
    axis.legend()
    localise_ticks(fig, locale)
    save(fig, "e2-confidence", locale)


FIGURES = (
    ("E5 sweep", localisation_sweep,
     ("localisation-sweep-workbook.csv", "localisation-sweep-catalogue.csv")),
    ("E6 throughput", throughput_by_book,
     ("throughput.csv", "throughput-by-book.csv")),
    ("E2 confidence", correction_confidence, ("correction-verdicts.csv",)),
)


def main() -> None:
    setup()
    for label, draw, needs in FIGURES:
        if not have(*needs):
            print(f"  skipped {label}: {', '.join(needs)} not measured yet")
            continue
        for locale in LABELS:
            draw(locale)


if __name__ == "__main__":
    main()
