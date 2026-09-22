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

from figures.style import BLUE, FAMILY, GREY, LIGHT, RED, RESULTS, TEAL, save, setup


def rows(name: str) -> list[dict[str, str]]:
    with open(RESULTS / name, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def have(*names: str) -> bool:
    return all((RESULTS / name).exists() for name in names)


def localisation_sweep() -> None:
    """E5: precision and coverage against the accept threshold, per cohort.

    The sweep is E5's real result. A single threshold observed once is not a
    decision boundary; the curve is, and it shows what coverage costs.

    Points where nothing is accepted are dropped rather than drawn. Precision
    over an empty accept set is 0/0, and the CSV writes it as 0.0; plotting
    that would show the precision collapsing at a high threshold when what
    collapsed is the denominator.
    """
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(5.2, 2.5), sharex=True, height_ratios=[1, 1]
    )
    for cohort, colour in (("workbook", BLUE), ("catalogue", RED)):
        data = [r for r in rows(f"localisation-sweep-{cohort}.csv")
                if int(r["accepted"]) > 0]
        x = [float(r["threshold"]) for r in data]
        top.plot(x, [float(r["precision"]) * 100 for r in data], color=colour,
                 label=cohort)
        bottom.plot(x, [float(r["coverage"]) * 100 for r in data], color=colour)

    # MIN_SCORE, the threshold the system actually runs at.
    for axis in (top, bottom):
        axis.axvline(0.808, color=GREY, lw=0.8, ls=":", zorder=0)
    top.text(0.812, 98.35, "operating point", color=GREY, fontsize=7, va="bottom")

    top.set_ylabel("precision (%)")
    top.set_ylim(98.2, 100.3)
    top.legend(loc="lower left")
    bottom.set_ylabel("coverage (%)")
    bottom.set_xlabel("accept threshold")
    bottom.set_ylim(-3, 105)
    for axis in (top, bottom):
        axis.margins(x=0.01)
    save(fig, "e5-sweep")


def throughput_by_book() -> None:
    """E6: seconds per page, one bar per book, coloured by type family.

    The pooled mean answers how fast; this answers how evenly, and the spread
    across 24 books is what a single mean hides.
    """
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
        24.6, float(pooled["all"]["seconds_per_page"]), "corpus mean",
        color=RED, fontsize=7, va="bottom",
    )
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=FAMILY[f], label=f"family {f}")
        for f in ("A", "B")
    ]
    axis.legend(handles=handles, loc="upper left", ncols=2)
    axis.set_ylabel("seconds per page")
    axis.set_xlabel("book")
    axis.set_xticks([1, 6, 12, 18, 24])
    axis.set_xlim(0.2, 28.5)
    axis.set_ylim(0, 2.45)
    save(fig, "e6-throughput")


def correction_confidence() -> None:
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
    fig, axis = plt.subplots(figsize=(5.2, 1.7))
    bins = [i / 20 for i in range(0, 13)]
    axis.hist(
        [accepted, rejected], bins=bins, color=[BLUE, RED], density=True,
        label=[f"accepted ({len(accepted)})", f"rejected ({len(rejected)})"],
    )
    axis.set_xlabel("lowest character confidence on the line")
    axis.set_ylabel("density")
    axis.legend()
    save(fig, "e2-confidence")


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
        draw()


if __name__ == "__main__":
    main()
