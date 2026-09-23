"""The gold set: which corrected pages may be scored, and what they hold.

A page is scorable only if a human corrected it and the recognition model never
read it. Transkribus records the first as a page status of `DONE`. It records
nothing at all about the second, so `data/gold/splits/training-pages.csv` does
that job: it lists every page the model trained on, and a page in that list is
refused however well it is corrected.

What this cannot establish is independence. Every page here was corrected on top
of some model's own output, and the model that produced that output is recorded
per page in the manifest's `seeded_by` column. The reference is post-edited, not
blind, and it is biased towards whichever system produced the seed: an error
that reads plausibly survives correction. Recording the seed per page is what
turns that bias from an admission into something a later pass can measure.

The line segmentation is Transkribus's too, not this harness's, so any later
comparison against Transkribus inherits its line boxes. That is the second thing
the seed column exists to make visible. `data/gold/GUIDELINES.md` states both
beside the transcription convention the pages follow.
"""

import csv
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Mapping
from xml.etree import ElementTree

PAGE_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"
_NS = {"p": PAGE_NS}

#: The only page status Transkribus sets when a human has finished a page.
CORRECTED = "DONE"

_READING_ORDER = re.compile(r"readingOrder\s*\{\s*index\s*:\s*(\d+)\s*;?\s*\}")
_MODEL = re.compile(r"model_id=(\d+)")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class GoldPage:
    """One corrected page, with the provenance that decides whether it counts."""

    page_id: str
    doc_id: str
    page_nr: int
    status: str
    last_change: str
    seeded_by: str
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        """The page as the scorer reads it, one reference line per printed line."""
        return "\n".join(self.lines)

    @property
    def chars(self) -> int:
        return len(_WHITESPACE.sub(" ", self.text).strip())

    @property
    def words(self) -> int:
        return len(self.text.split())


def _line_index(line: ElementTree.Element, fallback: int) -> int:
    match = _READING_ORDER.search(line.get("custom") or "")
    return int(match.group(1)) if match else fallback


def read_page(path: str | Path) -> GoldPage:
    """Read one PAGE XML file into a `GoldPage`.

    Lines come back in reading order rather than document order. The two agree
    in every file exported so far, but the reading order is the one the format
    promises, and a page whose regions were re-ordered by hand would break the
    other.
    """
    root = ElementTree.parse(path).getroot()

    metadata = root.find("p:Metadata", _NS)
    creator = metadata.findtext("p:Creator", default="", namespaces=_NS)
    last_change = metadata.findtext("p:LastChange", default="", namespaces=_NS)
    transkribus = metadata.find("p:TranskribusMetadata", _NS)

    doc_id = transkribus.get("docId", "")
    page_nr = int(transkribus.get("pageNr", "0"))
    model = _MODEL.search(creator)

    lines: list[tuple[int, str]] = []
    for position, line in enumerate(root.iter(f"{{{PAGE_NS}}}TextLine")):
        unicode_text = line.find("p:TextEquiv/p:Unicode", _NS)
        if unicode_text is None or not unicode_text.text:
            continue
        lines.append((_line_index(line, position), unicode_text.text))

    return GoldPage(
        # The id's first field is the Transkribus document, so a claim about
        # which work a page came from stays checkable against the manifest.
        page_id=f"{doc_id}_{Path(path).stem}",
        doc_id=doc_id,
        page_nr=page_nr,
        status=transkribus.get("status", ""),
        last_change=last_change,
        seeded_by=model.group(1) if model else "",
        lines=tuple(text for _, text in sorted(lines, key=lambda pair: pair[0])),
    )


def read_pages(directory: str | Path) -> Iterator[GoldPage]:
    """Read every PAGE XML file in an exported `page/` directory, page order."""
    for path in sorted(Path(directory).glob("*.xml")):
        yield read_page(path)


def read_exclusions(path: str | Path) -> dict[str, str]:
    """Page ids kept out of the frame, mapped to the reason they are out."""
    with open(path, encoding="utf-8", newline="") as handle:
        return {
            row["page_id"]: row["reason"]
            for row in csv.DictReader(handle)
            if row["page_id"]
        }


def refusal(
    page: GoldPage,
    *,
    trained_on: Iterable[str],
    excluded: dict[str, str],
) -> str | None:
    """Why this page may not be scored, or `None` if it may.

    The order matters only for the manifest's readability: a page that is both
    trained on and front matter is reported as trained on, because that is the
    reason that would still stand if the frame changed.
    """
    if page.page_id in set(trained_on):
        return "trained-on"
    if page.status != CORRECTED:
        return "not-corrected"
    if page.page_id in excluded:
        return excluded[page.page_id]
    if not page.lines:
        return "no-text"
    return None


def select(
    pages: Iterable[GoldPage],
    *,
    trained_on: Iterable[str],
    excluded: dict[str, str],
) -> list[tuple[GoldPage, str | None]]:
    """Every candidate page with its verdict, in page order.

    Refused pages are returned beside the kept ones rather than dropped, because
    `data/gold/GUIDELINES.md` requires each exclusion to be recorded.
    """
    seen = set(trained_on)
    return [
        (page, refusal(page, trained_on=seen, excluded=excluded))
        for page in sorted(pages, key=lambda p: (p.doc_id, p.page_nr))
    ]


#: The cohort name each Transkribus document is counted under.
COHORTS: dict[str, str] = {
    "10925942": "tresor1",
    "10926025": "tresor2",
    "16583795": "amadis13",
}

REFUSALS: tuple[str, ...] = ("trained-on", "not-corrected", "front-matter")


@dataclass(frozen=True)
class GoldSummary:
    """What one cohort contributes, kept and refused both."""

    cohort: str
    candidates: int
    pages: int
    lines: int
    chars: int
    words: int
    trained_on: int
    not_corrected: int
    excluded: int


def summarise(rows: Iterable[Mapping[str, str]]) -> list[GoldSummary]:
    """Summarise `MANIFEST.csv` per cohort, and over all of them.

    Read back from the manifest rather than from the pages, so that the figures
    in the report and the file that justifies each page cannot drift apart.
    """
    buckets: dict[str, list[Mapping[str, str]]] = {"all": []}
    for row in rows:
        buckets["all"].append(row)
        buckets.setdefault(COHORTS.get(row["doc_id"], row["doc_id"]), []).append(row)

    def summarise_one(cohort: str, group: list[Mapping[str, str]]) -> GoldSummary:
        kept = [row for row in group if row["kept"] == "yes"]
        reasons = Counter(row["reason"] for row in group if row["kept"] == "no")
        return GoldSummary(
            cohort=cohort,
            candidates=len(group),
            pages=len(kept),
            lines=sum(int(row["lines"]) for row in kept),
            chars=sum(int(row["chars"]) for row in kept),
            words=sum(int(row["words"]) for row in kept),
            trained_on=reasons["trained-on"],
            not_corrected=reasons["not-corrected"],
            excluded=sum(
                count for reason, count in reasons.items() if reason not in REFUSALS[:2]
            ),
        )

    order = ["all"] + [name for name in COHORTS.values() if name in buckets]
    return [summarise_one(name, buckets[name]) for name in order]


def read_manifest(path: str | Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_summary(rows: Iterable[GoldSummary], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["cohort", "candidates", "pages", "lines", "chars", "words",
             "trained_on", "not_corrected", "excluded"]
        )
        for row in rows:
            writer.writerow(
                [row.cohort, row.candidates, row.pages, row.lines, row.chars,
                 row.words, row.trained_on, row.not_corrected, row.excluded]
            )
