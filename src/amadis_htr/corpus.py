"""The corpus, counted from what this repository actually holds.

Section 3 of the report describes the material the rest of the report is
measured on. Rule 1 governs a descriptive count exactly as it governs a
measured one, so every figure in that section is rendered from `corpus.csv`
and `training.csv`, and a figure this repository cannot derive does not reach
the page at all.

**Three of section 3's planned numbers are deliberately absent.** The baseline
text's 1,770 chapters and 3,646,003 word tokens, and the seed index's 518,743
seeds over 76,548 word types, are properties of a production database that is
not in scope here: `PROVENANCE.md` records that the only read taken from it was
the alignment export, and a census was not part of that read. Those three
numbers appear in the design spec's prose with nothing behind them, which is
the condition under which `PROVENANCE.md` already drops a figure. They have no
macro, so a draft that cites one fails the build. What replaces them is the
extract length the alignment export does support: a Trésor piece is a span in
the baseline text, and its two offsets are committed.

**The cohorts partition the aligned pieces, not the reference.** The reference
holds 457 pieces and the matcher returned a span for 453, so the `all` row's
`pieces` is larger than the two cohort rows combined and `unaligned` carries
the difference. A cohort row's `pieces` and `aligned` are equal by
construction, because a piece has a cohort only by way of the matcher.
"""

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from amadis_htr.ground_truth import CONFIDENCES, Reference

#: The splits `prepare_data.py` wrote, plus the total. `val` is validation and
#: never test: it selected the shipped checkpoint, which is why section 8 has a
#: paragraph about it and section 6 may not score on it.
SPLITS: tuple[str, ...] = ("train", "val")


@dataclass(frozen=True)
class Piece:
    """One Trésor piece, as the reference and the matcher together describe it.

    `cohort` and the two offsets are `None` for a piece the matcher returned
    nothing for. None is not zero: a zero-length span would say the matcher
    placed the piece and found it empty.
    """

    piece: int
    confidence: str
    livre: int | None
    cohort: str | None
    start: int | None
    end: int | None

    @property
    def chars(self) -> int | None:
        """The extract's length in code points, or None if it was not placed."""
        if self.start is None or self.end is None:
            return None
        return self.end - self.start


@dataclass(frozen=True)
class CorpusRow:
    cohort: str
    pieces: int
    aligned: int
    unaligned: int
    livres: int
    certain: int
    conjecture: int
    uncertain: int
    none: int
    chars_mean: float
    chars_median: float
    chars_min: int
    chars_max: int


@dataclass(frozen=True)
class TrainingRow:
    split: str
    pages: int
    collections: int


def read_pieces(
    references: Mapping[int, Reference], alignments: str | Path
) -> list[Piece]:
    """Join the editor's reference to the matcher's frozen export.

    The reference is the frame: a piece the matcher invented and the editor
    never catalogued would be a bug in the export rather than a corpus fact,
    so it raises instead of quietly enlarging the corpus.
    """
    placed: dict[int, dict[str, str]] = {}
    with open(alignments, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            placed[int(row["piece"])] = row
    unknown = sorted(set(placed) - set(references))
    if unknown:
        raise KeyError(
            f"{len(unknown)} aligned pieces are not in the reference "
            f"({unknown[:5]}...). The reference is the frame for the corpus, "
            "so an alignment outside it is an export fault, not a piece."
        )
    pieces: list[Piece] = []
    for number in sorted(references):
        reference = references[number]
        row = placed.get(number)
        pieces.append(
            Piece(
                piece=number,
                confidence=reference.confidence,
                livre=reference.livre,
                cohort=row["cohort"] if row else None,
                start=int(row["start"]) if row else None,
                end=int(row["end"]) if row else None,
            )
        )
    return pieces


def _corpus_row(cohort: str, pieces: Sequence[Piece]) -> CorpusRow:
    lengths = [p.chars for p in pieces if p.chars is not None]
    aligned = len(lengths)
    bands = {c: sum(1 for p in pieces if p.confidence == c) for c in CONFIDENCES}
    return CorpusRow(
        cohort=cohort,
        pieces=len(pieces),
        aligned=aligned,
        unaligned=len(pieces) - aligned,
        livres=len({p.livre for p in pieces if p.livre is not None}),
        certain=bands["certain"],
        conjecture=bands["conjecture"],
        uncertain=bands["uncertain"],
        none=bands["none"],
        # A cohort with nothing placed has no mean extract, and reporting 0
        # would say its pieces are empty rather than absent. The row still
        # exists so the denominators above are visible.
        chars_mean=statistics.mean(lengths) if lengths else 0.0,
        chars_median=statistics.median(lengths) if lengths else 0.0,
        chars_min=min(lengths) if lengths else 0,
        chars_max=max(lengths) if lengths else 0,
    )


def summarise_corpus(
    pieces: Iterable[Piece], cohorts: Sequence[str]
) -> list[CorpusRow]:
    """One row per cohort, then one for the whole reference.

    `cohorts` is passed in rather than discovered, so a cohort the matcher
    stopped emitting produces a row of zeroes that a reader can see instead of
    vanishing from the table.
    """
    pieces = list(pieces)
    rows = [
        _corpus_row(cohort, [p for p in pieces if p.cohort == cohort])
        for cohort in cohorts
    ]
    rows.append(_corpus_row("all", pieces))
    return rows


def read_training_pages(path: str | Path) -> list[tuple[str, str]]:
    """Read the re-derived split as `(page_id, split)` pairs."""
    with open(path, encoding="utf-8", newline="") as handle:
        return [(row["page_id"], row["split"]) for row in csv.DictReader(handle)]


def summarise_training(pages: Iterable[tuple[str, str]]) -> list[TrainingRow]:
    """One row per split, then one for the whole training corpus.

    `collections` counts the Transkribus collections the pages came from, which
    is the claim section 3 makes about the training material: it is one
    collection, *Trésor des Amadis* T.1, and not a mixture. The collection is
    the page id's first field.
    """
    pages = list(pages)

    def row(split: str, subset: Sequence[tuple[str, str]]) -> TrainingRow:
        return TrainingRow(
            split=split,
            pages=len(subset),
            collections=len({page_id.split("_")[0] for page_id, _ in subset}),
        )

    rows = [row(split, [p for p in pages if p[1] == split]) for split in SPLITS]
    rows.append(row("all", pages))
    return rows


def write_corpus(rows: Iterable[CorpusRow], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["cohort", "pieces", "aligned", "unaligned", "livres", "certain",
             "conjecture", "uncertain", "none", "chars_mean", "chars_median",
             "chars_min", "chars_max"]
        )
        for row in rows:
            writer.writerow(
                [row.cohort, row.pieces, row.aligned, row.unaligned, row.livres,
                 row.certain, row.conjecture, row.uncertain, row.none,
                 f"{row.chars_mean:.1f}", f"{row.chars_median:.1f}",
                 row.chars_min, row.chars_max]
            )


def write_training(rows: Iterable[TrainingRow], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["split", "pages", "collections"])
        for row in rows:
            writer.writerow([row.split, row.pages, row.collections])
