"""`eval/results/*.csv` into `report/generated/macros.tex`, and its French
twin `report/generated/fr/macros.tex`.

Rule 1 of the repository architecture, made runnable: no number in the report
is typed by hand. Every registry that has a schema is rendered here, and a
registry whose CSV the evaluation has not produced fails loudly rather than
emitting a macro with nothing behind it.

    uv run python eval/render_macros.py
"""

from pathlib import Path

from amadis_htr.report_macros import (
    ALL_MACROS,
    LOCALES,
    render_macros,
    write_generated,
)

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "eval/results"
MACROS = {
    "en": REPO / "report/generated/macros.tex",
    "fr": REPO / "report/generated/fr/macros.tex",
}


def main() -> None:
    for locale in LOCALES:
        body = render_macros(ALL_MACROS, RESULTS, locale) if ALL_MACROS else ""
        write_generated(body, MACROS[locale])
        print(f"{len(ALL_MACROS)} macros written to "
              f"{MACROS[locale].relative_to(REPO)}")


if __name__ == "__main__":
    main()
