"""E6's CSVs, from the frozen OCR run records.

    uv run python eval/throughput_results.py
"""

from pathlib import Path

from amadis_htr.throughput import (
    read_runs,
    read_structures,
    summarise_structure,
    summarise_throughput,
    write_runs,
    write_structure,
    write_throughput,
)

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "data/runs/ocr"
RESULTS = REPO / "eval/results"


def main() -> None:
    runs = read_runs(RUNS)
    throughput = summarise_throughput(runs)
    structure = summarise_structure(read_structures(RUNS))
    write_throughput(throughput, RESULTS / "throughput.csv")
    write_structure(structure, RESULTS / "structure.csv")
    write_runs(runs, RESULTS / "throughput-by-book.csv")

    whole = next(r for r in throughput if r.cohort == "all")
    print(
        f"{whole.books} books, {whole.pages:,} pages, {whole.failed} failed, "
        f"{whole.seconds / 3600:.2f} hours, {whole.seconds_per_page:.3f} s/page"
    )
    for row in structure:
        print(
            f"family {row.cohort}: {row.matched} of {row.toc_chapters} chapters "
            f"recalled ({row.recall:.1%}), precision {row.precision:.1%}"
        )


if __name__ == "__main__":
    main()
