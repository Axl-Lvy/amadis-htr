"""`eval/results/*.csv` into `report/generated/macros.tex`.

Rule 1 of the repository architecture, made runnable: no number in the report
is typed by hand. Every registry that has a schema is rendered here, and a
registry whose CSV the evaluation has not produced fails loudly rather than
emitting a macro with nothing behind it.

    uv run python eval/render_macros.py
"""

from pathlib import Path

from amadis_htr.report_macros import (
    LOCALISATION_MACROS,
    render_macros,
    write_generated,
)

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "eval/results"
MACROS = REPO / "report/generated/macros.tex"

#: Every registry with a measured CSV behind it. E1, E2, E3, E4 and E6 join
#: this list when they first write to `eval/results/`, not before: a registry
#: declared ahead of its data is a guess about the data.
REGISTRIES = (LOCALISATION_MACROS,)


def main() -> None:
    macros = [macro for registry in REGISTRIES for macro in registry]
    body = render_macros(macros, RESULTS) if macros else ""
    write_generated(body, MACROS)
    print(f"{len(macros)} macros written to {MACROS.relative_to(REPO)}")


if __name__ == "__main__":
    main()
