"""E6: throughput and structural quality, from the harness's own records.

Descriptive only. These are counts and timings the OCR harness wrote while it
transcribed the 24 books, not a measurement against a reference, so nothing
here is an accuracy and the report may not read one into it.

**The two families are not comparable on structure.** Books 1 to 12 (family A)
carry a printed table of contents the harness could calibrate against, and
books 13 to 24 (family B) do not: their `calibration.json` has no `toc` and no
`match` block at all. A pooled structural figure would therefore be family A's
figure wearing the whole corpus's denominator, and family B's absence is a
property of the books rather than a failure of the run. Throughput pools
across both because a page is a page; structure does not.
"""

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

#: Books 1 to 12 print a table of contents; 13 to 24 do not.
FAMILIES: tuple[str, ...] = ("A", "B")


@dataclass(frozen=True)
class Run:
    """One book's transcription run."""

    book: int
    family: str
    pages: int
    failed: int
    seconds: float
    passages: int
    unresolved_ambiguous: int


@dataclass(frozen=True)
class Structure:
    """One book's structural calibration.

    `toc_chapters` and the match counts are `None` for family B, which has no
    printed table of contents to calibrate against. None is not zero: zero
    would say the harness looked and found nothing.
    """

    book: int
    family: str
    pages: int
    body: int
    header: int
    footer: int
    title: int
    empty_pages: int
    anomalies: int
    toc_chapters: int | None
    matched: int | None
    missing: int | None
    spurious: int | None
    unscorable: int | None


@dataclass(frozen=True)
class ThroughputRow:
    cohort: str
    books: int
    pages: int
    failed: int
    seconds: float
    seconds_per_page: float
    passages: int


@dataclass(frozen=True)
class StructureRow:
    cohort: str
    books: int
    pages: int
    toc_chapters: int
    matched: int
    missing: int
    spurious: int
    recall: float
    precision: float


def read_runs(root: str | Path) -> list[Run]:
    """Read every frozen `run.json`, paired with its book's family."""
    root = Path(root)
    runs: list[Run] = []
    for directory in sorted(
        (d for d in root.iterdir() if d.is_dir()),
        key=lambda d: int(d.name.split("-")[1]),
    ):
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        calibration = json.loads(
            (directory / "calibration.json").read_text(encoding="utf-8")
        )
        runs.append(
            Run(
                book=calibration["book"],
                family=calibration["family"],
                pages=run["pagesRun"],
                failed=run["pagesFailed"],
                seconds=run["seconds"],
                passages=run["passages"],
                unresolved_ambiguous=run["unresolvedAmbiguous"],
            )
        )
    return runs


def read_structures(root: str | Path) -> list[Structure]:
    """Read every frozen `calibration.json`."""
    root = Path(root)
    out: list[Structure] = []
    for directory in sorted(
        (d for d in root.iterdir() if d.is_dir()),
        key=lambda d: int(d.name.split("-")[1]),
    ):
        d = json.loads((directory / "calibration.json").read_text(encoding="utf-8"))
        structural = d["structural"]
        roles = structural["roleCounts"]
        anomalies = structural["anomalies"]
        match = d.get("match")
        out.append(
            Structure(
                book=d["book"],
                family=d["family"],
                pages=structural["pages"],
                body=roles.get("body", 0),
                header=roles.get("header", 0),
                footer=roles.get("footer", 0),
                title=roles.get("title", 0),
                empty_pages=sum(1 for a in anomalies if a["kind"] == "emptyPage"),
                anomalies=len(anomalies),
                toc_chapters=match["tocChapters"] if match else None,
                matched=len(match["matched"]) if match else None,
                missing=len(match["missing"]) if match else None,
                spurious=len(match["spurious"]) if match else None,
                unscorable=match["unscorable"] if match else None,
            )
        )
    return out


def _throughput_row(cohort: str, runs: Sequence[Run]) -> ThroughputRow:
    pages = sum(r.pages for r in runs)
    seconds = sum(r.seconds for r in runs)
    return ThroughputRow(
        cohort=cohort,
        books=len(runs),
        pages=pages,
        failed=sum(r.failed for r in runs),
        seconds=seconds,
        seconds_per_page=seconds / pages if pages else 0.0,
        passages=sum(r.passages for r in runs),
    )


def summarise_throughput(runs: Iterable[Run]) -> list[ThroughputRow]:
    """One row per family and one for the corpus.

    Pooling is legitimate here: every book was run by one model on one device
    at one working width, which `INDEX.csv` records and
    `tests/test_throughput.py` asserts.
    """
    runs = list(runs)
    rows = [
        _throughput_row(family, [r for r in runs if r.family == family])
        for family in FAMILIES
    ]
    rows.append(_throughput_row("all", runs))
    return rows


def summarise_structure(structures: Iterable[Structure]) -> list[StructureRow]:
    """One row per family that has a printed table of contents, and no other.

    A family with nothing to calibrate against produces no row rather than a
    row of zeroes, and there is deliberately no `all` row: see the module
    docstring.
    """
    structures = list(structures)
    rows: list[StructureRow] = []
    for family in FAMILIES:
        group = [
            s
            for s in structures
            if s.family == family and s.toc_chapters is not None
        ]
        if not group:
            continue
        toc = sum(s.toc_chapters for s in group)
        matched = sum(s.matched for s in group)
        spurious = sum(s.spurious for s in group)
        rows.append(
            StructureRow(
                cohort=family,
                books=len(group),
                pages=sum(s.pages for s in group),
                toc_chapters=toc,
                matched=matched,
                missing=sum(s.missing for s in group),
                spurious=spurious,
                recall=matched / toc if toc else 0.0,
                precision=matched / (matched + spurious) if matched + spurious else 0.0,
            )
        )
    return rows


def write_throughput(rows: Iterable[ThroughputRow], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["cohort", "books", "pages", "failed", "seconds",
             "seconds_per_page", "passages"]
        )
        for row in rows:
            writer.writerow(
                [row.cohort, row.books, row.pages, row.failed,
                 f"{row.seconds:.1f}", f"{row.seconds_per_page:.6f}",
                 row.passages]
            )


def write_structure(rows: Iterable[StructureRow], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["cohort", "books", "pages", "toc_chapters", "matched", "missing",
             "spurious", "recall", "precision"]
        )
        for row in rows:
            writer.writerow(
                [row.cohort, row.books, row.pages, row.toc_chapters,
                 row.matched, row.missing, row.spurious,
                 f"{row.recall:.6f}", f"{row.precision:.6f}"]
            )
