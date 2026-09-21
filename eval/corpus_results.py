"""Section 3's CSVs, from the reference, the matcher export and the split.

    uv run python eval/corpus_results.py
"""

from pathlib import Path

from amadis_htr.corpus import (
    read_pieces,
    read_training_pages,
    summarise_corpus,
    summarise_training,
    write_corpus,
    write_training,
)
from amadis_htr.localisation import read_ground_truth
from amadis_htr.report_macros import COHORTS

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "eval/results"


def main() -> None:
    pieces = read_pieces(
        read_ground_truth(REPO / "data/localisation/ground-truth.csv"),
        REPO / "data/runs/matcher/alignments.csv",
    )
    corpus = summarise_corpus(pieces, COHORTS)
    training = summarise_training(
        read_training_pages(REPO / "data/gold/splits/training-pages.csv")
    )
    write_corpus(corpus, RESULTS / "corpus.csv")
    write_training(training, RESULTS / "training.csv")

    whole = next(r for r in corpus if r.cohort == "all")
    print(
        f"{whole.pieces} pieces over {whole.livres} Livres, {whole.aligned} "
        f"aligned, {whole.certain} certain, extracts {whole.chars_min} to "
        f"{whole.chars_max} code points (mean {whole.chars_mean:.0f})"
    )
    for row in corpus:
        if row.cohort != "all":
            print(
                f"  {row.cohort}: {row.aligned} pieces, mean "
                f"{row.chars_mean:.0f} code points"
            )
    pages = next(r for r in training if r.split == "all")
    print(f"{pages.pages} training pages from {pages.collections} collection")


if __name__ == "__main__":
    main()
