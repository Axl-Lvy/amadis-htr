"""One look for every figure in the report and the deck.

The palette is the report's own (`report/preamble.tex`), so a figure does not
arrive on the page as a foreign object. Everything else here is subtraction:
no gridlines behind the data, no box around the axes, no legend frame, no
title inside the figure. A LaTeX float already has a caption, and a title
inside the image would print the same sentence twice.

Figures are written as PDF. They are vector, they embed no raster, and they
scale to whatever column width the report gives them.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import ScalarFormatter  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "eval/results"
OUT = {
    "en": REPO / "report/generated/figures",
    "fr": REPO / "report/generated/fr/figures",
}

#: report/preamble.tex, definecolor reportblue / reportred / reportteal.
BLUE = "#003E5C"
RED = "#D52B1E"
TEAL = "#006880"
GREY = "#8A8A8A"
LIGHT = "#D9D9D9"

#: Family A is blue and family B is teal, everywhere, in every figure.
FAMILY = {"A": BLUE, "B": TEAL, "all": GREY}


def setup() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
            "font.family": "serif",
            "font.serif": ["Libertinus Serif", "Linux Libertine O", "DejaVu Serif"],
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#444444",
            "axes.linewidth": 0.6,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.frameon": False,
            "lines.linewidth": 1.4,
        }
    )


class DecimalComma(ScalarFormatter):
    """Tick labels with a decimal comma, for the French report.

    Not matplotlib's `useLocale`, which reads the machine's locale and so would
    draw a different figure on a different machine.
    """

    def __call__(self, x, pos=None):
        return super().__call__(x, pos).replace(".", ",")


def localise_ticks(fig, locale: str) -> None:
    """Give every axis of a figure the decimal mark of `locale`."""
    if locale == "en":
        return
    for axis in fig.axes:
        axis.xaxis.set_major_formatter(DecimalComma())
        axis.yaxis.set_major_formatter(DecimalComma())


def save(fig, name: str, locale: str = "en") -> Path:
    """Write one figure, and say where it went.

    `CreationDate: None` drops the timestamp matplotlib would otherwise stamp
    into the PDF. Without it a figure redrawn from unchanged inputs differs
    from the committed copy on every run, and `git diff` after
    `eval/run_all.sh` -- the repository's own check that nothing drifted --
    would report a change on every figure, every time, and so report nothing.
    """
    OUT[locale].mkdir(parents=True, exist_ok=True)
    path = OUT[locale] / f"{name}.pdf"
    fig.savefig(path, metadata={"CreationDate": None})
    plt.close(fig)
    print(f"  {path.relative_to(REPO)}")
    return path
