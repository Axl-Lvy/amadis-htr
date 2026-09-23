"""E5: scoring the matcher against the editor's own reference.

The matcher runs in the amadis repository against the production database, so
its output arrives here as a frozen artefact, `data/runs/matcher/alignments.csv`
with the header `piece,livre,chapter,start,end,score`.

The sweep is the point of this module. A single accept threshold observed once
on curated data is not a decision boundary. A precision-against-coverage curve
is, and it lets the report state the false-positive rate that comes with any
threshold it recommends.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from amadis_htr.ground_truth import CONFIDENCES, Reference

#: The accept thresholds the sweep reports, 0.40 to 1.00 in hundredths.
#:
#: Built by dividing integers rather than by adding 0.01 repeatedly. Repeated
#: addition reaches 0.8600000000000001 at the forty-seventh step, and a piece
#: scoring exactly 0.86 then falls on the other side of `score < threshold`,
#: which moves one accepted piece in the catalogue cohort. The sweep is a
#: decision boundary, so its thresholds are the numbers they are printed as.
SWEEP_THRESHOLDS: tuple[float, ...] = tuple(x / 100 for x in range(40, 101))


@dataclass(frozen=True)
class Prediction:
    piece: int
    livre: int | None
    chapter: int | None
    score: float


@dataclass(frozen=True)
class Summary:
    confidence: str
    total: int
    located: int
    livre_correct: int
    chapter_scoreable: int
    chapter_correct: int
    chapter_unavailable: int
    #: The editor catalogued the piece to a Livre and named no chapter, so
    #: there is no reference to score against. Distinct from
    #: `chapter_unavailable`, where the reference has a chapter and the
    #: printed label the matcher landed on could not be decoded. Without this
    #: column the three do not sum to `total` and the missing piece looks like
    #: a scorer fault.
    chapter_unreferenced: int


@dataclass(frozen=True)
class SweepRow:
    threshold: float
    accepted: int
    correct: int
    precision: float
    coverage: float


def _optional_int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def read_ground_truth(path: str | Path) -> dict[int, Reference]:
    """Read the table the extraction step wrote."""
    out: dict[int, Reference] = {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            piece = int(row["piece"])
            out[piece] = Reference(
                piece=piece,
                livre=_optional_int(row["livre"]),
                chapter=_optional_int(row["chapter"]),
                confidence=row["confidence"],
                raw=row["raw"],
            )
    return out


def read_predictions(path: str | Path) -> dict[int, Prediction]:
    """Read the frozen matcher output."""
    out: dict[int, Prediction] = {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            piece = int(row["piece"])
            out[piece] = Prediction(
                piece=piece,
                livre=_optional_int(row["livre"]),
                chapter=_optional_int(row["chapter"]),
                score=float(row["score"] or 0.0),
            )
    return out


def read_predictions_by_cohort(
    path: str | Path,
) -> dict[str, dict[int, Prediction]]:
    """The same output, split on the import batch it came from.

    The two batches are not one test set. The gate was pre-registered on the
    workbook batch when it was the only one, so pooling them would be scoring
    against a test set enlarged after the numbers were seen. Every figure the
    report states is therefore per cohort, and this is where they part.
    """
    out: dict[str, dict[int, Prediction]] = {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            piece = int(row["piece"])
            out.setdefault(row["cohort"], {})[piece] = Prediction(
                piece=piece,
                livre=_optional_int(row["livre"]),
                chapter=_optional_int(row["chapter"]),
                score=float(row["score"] or 0.0),
            )
    return out


def references_for(
    references: Mapping[int, Reference], predictions: Mapping[int, Prediction]
) -> dict[int, Reference]:
    """The reference rows one cohort is scored against.

    A cohort is scored only on the pieces it holds. Keeping the other cohort's
    references in the denominator would count every piece it never imported as
    a piece this one failed to locate.
    """
    return {p: r for p, r in references.items() if p in predictions}


def summarise(
    references: Mapping[int, Reference], predictions: Mapping[int, Prediction]
) -> list[Summary]:
    """One row per confidence band, so no piece is silently dropped."""
    rows: list[Summary] = []
    for confidence in CONFIDENCES:
        group = [r for r in references.values() if r.confidence == confidence]
        located = livre_correct = chapter_scoreable = chapter_correct = 0
        chapter_unavailable = chapter_unreferenced = 0
        for ref in group:
            pred = predictions.get(ref.piece)
            if pred is None or pred.livre is None:
                continue
            located += 1
            if ref.livre is None:
                continue
            if pred.livre == ref.livre:
                livre_correct += 1
            if ref.chapter is None:
                chapter_unreferenced += 1
                continue
            if pred.chapter is None:
                # `decodeChapterLabel` recovers a printed number from 61% of the
                # labels. Where it recovers none there is nothing to compare, and
                # counting that as a miss would score the printed edition's
                # legibility rather than the matcher.
                chapter_unavailable += 1
                continue
            chapter_scoreable += 1
            if pred.livre == ref.livre and pred.chapter == ref.chapter:
                chapter_correct += 1
        rows.append(
            Summary(
                confidence=confidence,
                total=len(group),
                located=located,
                livre_correct=livre_correct,
                chapter_scoreable=chapter_scoreable,
                chapter_correct=chapter_correct,
                chapter_unavailable=chapter_unavailable,
                chapter_unreferenced=chapter_unreferenced,
            )
        )
    return rows


def sweep(
    references: Mapping[int, Reference],
    predictions: Mapping[int, Prediction],
    thresholds: Sequence[float],
) -> list[SweepRow]:
    """Precision against coverage over accept thresholds, on the certain rows.

    Coverage is the share of scoreable pieces the threshold admits. Precision is
    the share of admitted pieces whose Livre is right.
    """
    scoreable = [
        r
        for r in references.values()
        if r.confidence == "certain" and r.livre is not None
    ]
    rows: list[SweepRow] = []
    for threshold in thresholds:
        accepted = correct = 0
        for ref in scoreable:
            pred = predictions.get(ref.piece)
            if pred is None or pred.livre is None or pred.score < threshold:
                continue
            accepted += 1
            if pred.livre == ref.livre:
                correct += 1
        rows.append(
            SweepRow(
                threshold=threshold,
                accepted=accepted,
                correct=correct,
                precision=correct / accepted if accepted else 0.0,
                coverage=accepted / len(scoreable) if scoreable else 0.0,
            )
        )
    return rows


def write_summary(rows: Iterable[Summary], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "confidence",
                "total",
                "located",
                "livre_correct",
                "chapter_scoreable",
                "chapter_correct",
                "chapter_unavailable",
                "chapter_unreferenced",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.confidence,
                    row.total,
                    row.located,
                    row.livre_correct,
                    row.chapter_scoreable,
                    row.chapter_correct,
                    row.chapter_unavailable,
                    row.chapter_unreferenced,
                ]
            )


def write_sweep(rows: Iterable[SweepRow], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["threshold", "accepted", "correct", "precision", "coverage"])
        for row in rows:
            writer.writerow(
                [
                    f"{row.threshold:.3f}",
                    row.accepted,
                    row.correct,
                    f"{row.precision:.6f}",
                    f"{row.coverage:.6f}",
                ]
            )


#: Roman numeral values, largest first, for `roman`.
_ROMAN = ((100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
          (5, "V"), (4, "IV"), (1, "I"))


def roman(number: int) -> str:
    """The number as the print writes it: 72 is LXXII."""
    out = []
    for value, letters in _ROMAN:
        while number >= value:
            out.append(letters)
            number -= value
    return "".join(out)


def _edit_distance(a: str, b: str) -> int:
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        previous, row[0] = row[:], i
        for j, cb in enumerate(b, 1):
            row[j] = min(previous[j] + 1, row[j - 1] + 1, previous[j - 1] + (ca != cb))
    return row[-1]


#: Two chapter numbers whose roman forms differ by at most this many letters
#: are what a misread heading produces: VI read as I, LXXII as LXII.
NUMERAL_CLOSE = 2


@dataclass(frozen=True)
class ChapterErrors:
    """Why the chapter figure misses, over the scoreable certain pieces.

    The chapter a prediction carries is the number decoded from the printed
    heading its span falls under, as the pipeline transcribed it. A miss can
    therefore come from the heading rather than the placement, and
    `numeral_close` counts the misses that look like that.
    """

    cohort: str
    scoreable: int
    correct: int
    wrong_livre: int
    numeral_close: int
    other: int


def chapter_errors(
    cohort: str,
    references: Mapping[int, Reference],
    predictions: Mapping[int, Prediction],
) -> ChapterErrors:
    scoreable = correct = wrong_livre = close = other = 0
    for piece, ref in references.items():
        pred = predictions.get(piece)
        if (ref.confidence != "certain" or pred is None or ref.livre is None
                or ref.chapter is None or pred.chapter is None):
            continue
        scoreable += 1
        if pred.livre != ref.livre:
            wrong_livre += 1
        elif pred.chapter == ref.chapter:
            correct += 1
        elif _edit_distance(roman(pred.chapter), roman(ref.chapter)) <= NUMERAL_CLOSE:
            close += 1
        else:
            other += 1
    return ChapterErrors(cohort, scoreable, correct, wrong_livre, close, other)


def write_chapter_errors(rows: Iterable[ChapterErrors], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["cohort", "scoreable", "correct", "wrong_livre", "numeral_close", "other"]
        )
        for r in rows:
            writer.writerow(
                [r.cohort, r.scoreable, r.correct, r.wrong_livre, r.numeral_close,
                 r.other]
            )
