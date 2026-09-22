"""E2: what the marker-anchor accept rule did, from the frozen verdicts.

The claim under test is C2: wrapping a suspect span in `⟦ ⟧` and accepting a
reply only when everything outside the markers comes back byte identical keeps
a generative model from rewriting text it was not asked to touch. On
16th-century French that matters more than usual, because a model's instinct is
to modernise the spelling and the accept rule is what stops it.

**This is not an accuracy.** Scoring correction on against correction off needs
a reference transcription, and the gold set does not exist yet, so E2 reports
what the rule did and says nothing about whether the edits it kept are
improvements. `docs/pre-registration/2026-09-22-e2-correction-design.md` fixed
that limit before the run rather than leaving it to be found afterwards.

**Two denominators, and they are not interchangeable.** `reach` counts what the
pass would look at over the whole corpus: a deterministic property of the
recognition output, no model involved, all 14,111 pages. `verdicts` counts what
happened on the 400 sampled pages that were actually offered to the model. A
rate over one denominator may not be printed against the other, so the two have
separate CSVs and separate macro prefixes.

**One rejection reason is the claim and four are not.** `outside-changed` is
the rule catching a model that edited text outside the markers, which is the
failure C2 defends against. `unparsed`, `malformed-markers`, `span-count` and
`call-failed` are protocol failures: the reply never became a candidate edit at
all. Pooling them would let a flaky JSON parser inflate the headline.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

#: The type families, as everywhere else in this repository.
FAMILIES: tuple[str, ...] = ("A", "B")

#: Every branch of `accept_marker_anchored` that can refuse a reply, plus the
#: transport failure in front of it. Fixed here so a reason the run never
#: produced still gets a row of zeroes rather than vanishing from the table.
REASONS: tuple[str, ...] = (
    "outside-changed",
    "span-count",
    "malformed-markers",
    "unparsed",
    "call-failed",
)

#: A refusal moving more characters than this outside the markers is counted
#: as substantial. Two is the smallest edit that is not a single character
#: appearing, vanishing or changing -- a moved space, in other words. The
#: threshold is a reporting convention, declared here and used nowhere else.
SUBSTANTIAL: int = 2

#: The one reason that is evidence for C2. The other four say the reply was
#: never a candidate edit, not that the rule caught a rewrite.
REWRITE_REASON = "outside-changed"


@dataclass(frozen=True)
class Reach:
    """One page's suspect-span census, from the recognition output alone."""

    page_id: str
    book: int
    family: str
    lines: int
    correctable: int
    lines_with_span: int
    spans: int


@dataclass(frozen=True)
class Verdict:
    """One line offered to the model, and what the accept rule did with it."""

    page_id: str
    book: int
    family: str
    #: Index within the page's *correctable* lines, which is what the pipeline
    #: enumerates. Not the index into `page["lines"]`.
    correctable_index: int
    role: str
    spans: int
    span_chars: int
    min_conf: float
    #: False when `suspect_spans` fell back to locating words with `text.find`.
    #: That branch resolves two occurrences of one word to the same index, so
    #: the accept rule can pass a line whose text it has itself corrupted. The
    #: column exists to bound how much of the sample sits on that path.
    clean: bool
    parsed: bool
    accepted: bool
    reason: str
    #: How far outside the markers the reply moved, when it was refused for
    #: moving at all. A moved space and a rewritten clause share one reason;
    #: only these two numbers separate them.
    outside_segments: int
    outside_edits: int
    changed_spans: int
    changed_chars: int
    #: Wall clock under four-way contention. Not a throughput figure.
    seconds: float


@dataclass(frozen=True)
class ReachRow:
    cohort: str
    books: int
    pages: int
    pages_with_span: int
    lines: int
    correctable: int
    lines_with_span: int
    spans: int


@dataclass(frozen=True)
class VerdictRow:
    cohort: str
    pages: int
    offered: int
    spans_offered: int
    accepted: int
    rejected: int
    rewrites_caught: int
    protocol_failures: int
    accepted_unchanged: int
    changed_spans: int
    changed_chars: int
    #: How many offered lines sat on the unsafe `text.find` branch.
    on_find_fallback: int
    #: Summed over the refused-for-rewriting lines only, so the report can say
    #: how large those rewrites were rather than only how many there were.
    rewrite_edits: int
    rewrite_segments: int
    #: Refusals that moved more than `SUBSTANTIAL` characters outside the
    #: markers. Two totals over all refusals cannot separate "one long rewrite
    #: and many moved spaces" from "many uniform rewrites", and that is the
    #: distinction the headline rests on.
    rewrites_substantial: int


@dataclass(frozen=True)
class ReasonRow:
    reason: str
    lines: int


def read_reach(path: str | Path) -> list[Reach]:
    with open(path, encoding="utf-8", newline="") as handle:
        return [
            Reach(
                page_id=row["page_id"],
                book=int(row["book"]),
                family=row["family"],
                lines=int(row["lines"]),
                correctable=int(row["correctable"]),
                lines_with_span=int(row["lines_with_span"]),
                spans=int(row["spans"]),
            )
            for row in csv.DictReader(handle)
        ]


def read_verdicts(path: str | Path) -> list[Verdict]:
    with open(path, encoding="utf-8", newline="") as handle:
        return [
            Verdict(
                page_id=row["page_id"],
                book=int(row["book"]),
                family=row["family"],
                correctable_index=int(row["correctable_index"]),
                role=row["role"],
                spans=int(row["spans"]),
                span_chars=int(row["span_chars"]),
                min_conf=float(row["min_conf"]),
                clean=row["clean"] == "1",
                parsed=row["parsed"] == "1",
                accepted=row["accepted"] == "1",
                reason=row["reason"],
                outside_segments=int(row["outside_segments"]),
                outside_edits=int(row["outside_edits"]),
                changed_spans=int(row["changed_spans"]),
                changed_chars=int(row["changed_chars"]),
                seconds=float(row["seconds"]),
            )
            for row in csv.DictReader(handle)
        ]


def _reach_row(cohort: str, pages: Sequence[Reach]) -> ReachRow:
    return ReachRow(
        cohort=cohort,
        books=len({p.book for p in pages}),
        pages=len(pages),
        pages_with_span=sum(1 for p in pages if p.spans),
        lines=sum(p.lines for p in pages),
        correctable=sum(p.correctable for p in pages),
        lines_with_span=sum(p.lines_with_span for p in pages),
        spans=sum(p.spans for p in pages),
    )


def summarise_reach(pages: Iterable[Reach]) -> list[ReachRow]:
    """One row per family and one for the corpus."""
    pages = list(pages)
    rows = [
        _reach_row(family, [p for p in pages if p.family == family])
        for family in FAMILIES
    ]
    rows.append(_reach_row("all", pages))
    return rows


def _verdict_row(cohort: str, verdicts: Sequence[Verdict]) -> VerdictRow:
    accepted = [v for v in verdicts if v.accepted]
    return VerdictRow(
        cohort=cohort,
        pages=len({v.page_id for v in verdicts}),
        offered=len(verdicts),
        spans_offered=sum(v.spans for v in verdicts),
        accepted=len(accepted),
        rejected=len(verdicts) - len(accepted),
        rewrites_caught=sum(1 for v in verdicts if v.reason == REWRITE_REASON),
        protocol_failures=sum(
            1 for v in verdicts if v.reason and v.reason != REWRITE_REASON
        ),
        # A model that returns the span untouched has agreed with the
        # recogniser. That is not a rejection and not a correction, and the
        # report needs it separate from both or the acceptance rate reads as an
        # edit rate.
        accepted_unchanged=sum(1 for v in accepted if v.changed_spans == 0),
        changed_spans=sum(v.changed_spans for v in accepted),
        changed_chars=sum(v.changed_chars for v in accepted),
        on_find_fallback=sum(1 for v in verdicts if not v.clean),
        rewrite_edits=sum(
            v.outside_edits for v in verdicts if v.reason == REWRITE_REASON
        ),
        rewrite_segments=sum(
            v.outside_segments for v in verdicts if v.reason == REWRITE_REASON
        ),
        rewrites_substantial=sum(
            1
            for v in verdicts
            if v.reason == REWRITE_REASON and v.outside_edits > SUBSTANTIAL
        ),
    )


def summarise_verdicts(verdicts: Iterable[Verdict]) -> list[VerdictRow]:
    """One row per family and one pooled."""
    verdicts = list(verdicts)
    rows = [
        _verdict_row(family, [v for v in verdicts if v.family == family])
        for family in FAMILIES
    ]
    rows.append(_verdict_row("all", verdicts))
    return rows


def summarise_reasons(verdicts: Iterable[Verdict]) -> list[ReasonRow]:
    """One row per rejection reason, in the fixed order, zeroes included."""
    verdicts = list(verdicts)
    return [
        ReasonRow(reason=reason, lines=sum(1 for v in verdicts if v.reason == reason))
        for reason in REASONS
    ]


def accept_rate_by_page(
    verdicts: Iterable[Verdict],
    *,
    hit: Callable[[Verdict], bool] = lambda v: v.accepted,
) -> list[tuple[str, int, int]]:
    """`(page_id, hits, offered)` per page, the bootstrap's resampling unit.

    Pages and not lines: the lines on one page share a scan, a forme and a
    stretch of type wear, so their verdicts are correlated and resampling lines
    would understate the interval.

    `hit` selects which event is counted, so the acceptance rate and the
    rewrite-caught rate use one clustering rather than two implementations of
    it.
    """
    pages: dict[str, list[int]] = {}
    for verdict in verdicts:
        entry = pages.setdefault(verdict.page_id, [0, 0])
        entry[0] += int(bool(hit(verdict)))
        entry[1] += 1
    return [(page, counts[0], counts[1]) for page, counts in sorted(pages.items())]


def write_reach(rows: Iterable[ReachRow], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["cohort", "books", "pages", "pages_with_span", "lines", "correctable",
             "lines_with_span", "spans"]
        )
        for row in rows:
            writer.writerow(
                [row.cohort, row.books, row.pages, row.pages_with_span, row.lines,
                 row.correctable, row.lines_with_span, row.spans]
            )


def write_verdicts(rows: Iterable[VerdictRow], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["cohort", "pages", "offered", "spans_offered", "accepted", "rejected",
             "rewrites_caught", "protocol_failures", "accepted_unchanged",
             "changed_spans", "changed_chars", "on_find_fallback",
             "rewrite_edits", "rewrite_segments", "rewrites_substantial"]
        )
        for row in rows:
            writer.writerow(
                [row.cohort, row.pages, row.offered, row.spans_offered, row.accepted,
                 row.rejected, row.rewrites_caught, row.protocol_failures,
                 row.accepted_unchanged, row.changed_spans, row.changed_chars,
                 row.on_find_fallback, row.rewrite_edits, row.rewrite_segments,
                 row.rewrites_substantial]
            )


def write_reasons(rows: Iterable[ReasonRow], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["reason", "lines"])
        for row in rows:
            writer.writerow([row.reason, row.lines])
