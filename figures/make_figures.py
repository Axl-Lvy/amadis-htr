"""Every figure in the report, from `eval/results/*.csv`.

Four figures and no more. A bar chart of two bars says what a sentence says,
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
        "workbook": "batch 1",
        "catalogue": "batch 2",
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
        "refused": "replies refused (%)",
        "lines": "{} lines",
        "epoch": "epoch",
        "validation cer": "validation CER (%)",
        "shipped": "reduce on plateau, $3\\times10^{-4}$",
        "constant": "constant, $10^{-3}$",
        "selected": "shipped checkpoint",
    },
    "fr": {
        "workbook": "lot 1",
        "catalogue": "lot 2",
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
        "refused": "réponses refusées (%)",
        "lines": "{} lignes",
        "epoch": "époque",
        "validation cer": "CER de validation (%)",
        "shipped": "réduction sur plateau, $3\\times10^{-4}$",
        "constant": "constant, $10^{-3}$",
        "selected": "modèle livré",
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
    """Correction: the share of replies refused, by the line's lowest confidence.

    One scale for every bar, and the number of lines written on each, so a
    small band cannot pass for a strong result.
    """
    words = LABELS[locale]
    bands = [r for r in rows("correction-confidence.csv") if r["band"] != "above"]
    fig, axis = plt.subplots(figsize=(5.2, 1.8))
    x = list(range(len(bands)))
    share = [100 * int(r["refused"]) / int(r["lines"]) for r in bands]
    axis.bar(x, share, color=BLUE, width=0.6)
    for i, (r, h) in enumerate(zip(bands, share)):
        axis.text(i, h + 0.6, words["lines"].format(int(r["lines"])),
                  ha="center", va="bottom", fontsize=7, color=GREY)
    tick = "{:.2f}–{:.2f}"
    axis.set_xticks(x, [tick.format(float(r["low"]), float(r["high"]))
                        for r in bands])
    axis.set_xlabel(words["confidence"])
    axis.set_ylabel(words["refused"])
    axis.set_ylim(0, max(share) * 1.3)
    localise_ticks(fig, locale)
    if locale == "fr":
        axis.set_xticklabels([t.get_text().replace(".", ",")
                              for t in axis.get_xticklabels()])
    save(fig, "e2-confidence", locale)


def training_curve(locale: str) -> None:
    """The fine-tune: validation CER per epoch, for both training runs.

    The y axis starts at zero so the gap between the runs is not exaggerated.
    """
    words = LABELS[locale]
    data = rows("training-curve.csv")
    best = {r["run"]: r for r in rows("training-runs.csv")}
    fig, axis = plt.subplots(figsize=(5.2, 1.8))
    for run, colour, label in (
        ("rop0.5-lr3e-4-augment", BLUE, words["shipped"]),
        ("run1-constant-lr0.001", RED, words["constant"]),
    ):
        curve = [r for r in data if r["run"] == run]
        axis.plot([int(r["epoch"]) for r in curve],
                  [float(r["cer"]) * 100 for r in curve],
                  color=colour, label=label, marker="." if len(curve) < 20 else None)
    chosen = best["rop0.5-lr3e-4-augment"]
    x, y = int(chosen["best_epoch"]), float(chosen["cer"]) * 100
    axis.plot([x], [y], "o", color=BLUE, ms=4, zorder=3)
    axis.annotate(words["selected"], (x, y), xytext=(x - 2, y + 0.45),
                  fontsize=7, color=GREY, ha="right",
                  arrowprops={"arrowstyle": "-", "color": GREY, "lw": 0.6})
    axis.set_xlabel(words["epoch"])
    axis.set_ylabel(words["validation cer"])
    axis.set_ylim(0, 1.75)
    axis.legend(loc="upper right")
    localise_ticks(fig, locale)
    save(fig, "training-curve", locale)


FIGURES = (
    ("Fine-tune curve", training_curve,
     ("training-curve.csv", "training-runs.csv")),
    ("E5 sweep", localisation_sweep,
     ("localisation-sweep-workbook.csv", "localisation-sweep-catalogue.csv")),
    ("E6 throughput", throughput_by_book,
     ("throughput.csv", "throughput-by-book.csv")),
    ("E2 confidence", correction_confidence, ("correction-confidence.csv",)),
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
