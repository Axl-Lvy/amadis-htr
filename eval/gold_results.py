"""`data/gold/MANIFEST.csv` into `eval/results/gold.csv`.

The manifest is the committed input, so this reruns anywhere without the
Transkribus exports. Rebuilding the set from the exports is a separate step,
`eval/build_gold_set.py`, because that one needs files this repository does not
carry.

    uv run python eval/gold_results.py
"""

from pathlib import Path

from amadis_htr.gold import read_manifest, summarise, write_summary

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "data/gold/MANIFEST.csv"
RESULTS = REPO / "eval/results"


def main() -> None:
    rows = summarise(read_manifest(MANIFEST))
    write_summary(rows, RESULTS / "gold.csv")

    overall = next(row for row in rows if row.cohort == "all")
    print(
        f"{overall.candidates:,} candidate pages, {overall.pages} kept: "
        f"{overall.lines:,} lines, {overall.chars:,} characters. "
        f"Refused {overall.trained_on} trained on, "
        f"{overall.not_corrected} uncorrected, {overall.excluded} excluded."
    )


if __name__ == "__main__":
    main()
