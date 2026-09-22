"""E2's run: offer every suspect line on the sampled pages, freeze the verdicts.

The accept rule is the pipeline's, imported and never restated here. This file
is a loop and a recorder: it walks the pages the manifest names, asks the
production prompt of the production model, and writes down what the production
rule did with the answer.

An LLM reply is not reproducible, so what is frozen is the verdict rather than
the reply, exactly as E6 freezes the harness's counts rather than the pages.
`data/runs/correction/VERDICTS.csv` is what every E2 figure then derives from,
deterministically and with no GPU.

**Pages run in parallel; lines within a page run in order.** The pipeline's
`correct_page` assigns the accepted text back onto the line as it walks a page,
so line *i+1* is sent with line *i* already corrected in its `PREV` slot.
Building every prompt up front would send uncorrected context everywhere and
measure a system that is not the one that ships. Concurrency therefore sits at
the page, where the pipeline has no cross-page state at all.

`offer_page` is module level rather than a closure so the suite can run it
against the pipeline's own `correct_page` on the same page with the same
scripted replies. A harness that cannot be compared to the thing it measures is
a second implementation wearing a test.

**The record carries no text.** Not the line, not the reply, not the corrected
span. Identifiers, counts, confidences, the verdict and the reason.

Three of the columns exist because a verdict alone is not auditable:

- `outside_edits` and `outside_segments` size a rejection. `outside-changed` is
  the one reason that is evidence for C2, but it fires on any byte difference
  outside the markers, which covers a 40-character rewrite and a moved space
  alike. Without the distance the headline cannot be defended, and the record
  holds no text to recover it from later.
- `clean` records which branch of the pipeline's `suspect_spans` located the
  spans. Its fallback resolves each suspect word with `text.find`, so two
  low-confidence occurrences of one word both resolve to the first, and the
  accept rule then compares a corrupted construction against itself and accepts
  it. That is a hole in the very property C2 claims, and E2 can at least bound
  how much of the sample sits on that path.

    uv run python eval/run_correction.py \
        --source "/path/to/Amadis de Gaule/ocr" \
        --pipeline /path/to/home-lab/hosts/bigpc/source_ocr_service
"""

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "data/runs/correction"

#: Registered in docs/pre-registration/2026-09-22-e2-correction-design.md.
#: Four, because eight measured slower on a saturated GPU.
WORKERS = 4

FIELDS = [
    "page_id", "book", "family",
    # The index within the page's *correctable* lines, which is what the
    # pipeline enumerates. It is not the index into page["lines"]: a page with
    # a header or a footer renumbers. Joining back to book.ndjson by this
    # column without re-applying the role filter lands on the wrong line.
    "correctable_index",
    "role", "spans", "span_chars", "min_conf", "clean", "parsed", "accepted",
    "reason", "outside_segments", "outside_edits", "changed_spans",
    "changed_chars",
    # Wall clock under four-way contention, so roughly four times the
    # sequential cost of one call. It is not a throughput figure and no macro
    # reads it.
    "seconds",
]


def load_pipeline(path: str) -> SimpleNamespace:
    """Import the production correction pass. Nothing here reimplements it."""
    sys.path.insert(0, path)
    from source_ocr.correction import (  # noqa: E402
        CORRECTABLE_ROLES,
        _split_marked,
        accept_marker_anchored,
        apply_line_correction,
        build_prompt,
        mark_text,
        parse_corrected,
        suspect_spans,
    )

    return SimpleNamespace(
        CORRECTABLE_ROLES=CORRECTABLE_ROLES,
        split_marked=_split_marked,
        accept=accept_marker_anchored,
        apply=apply_line_correction,
        build_prompt=build_prompt,
        mark_text=mark_text,
        parse_corrected=parse_corrected,
        suspect_spans=suspect_spans,
    )


def correctable(lines, fns) -> list:
    """The lines the pipeline would offer, by the pipeline's own filter."""
    return [
        line
        for line in (lines or [])
        if (line.get("role") or "body") in fns.CORRECTABLE_ROLES
        and isinstance(line.get("text"), str)
        and line["text"].strip()
    ]


def spans_are_clean(line) -> bool:
    """Whether `suspect_spans` located this line's spans by offset or by find.

    The pipeline's own condition, restated here as instrumentation rather than
    as logic: it decides nothing, it only records which branch ran. The `find`
    branch is the one that can emit two spans at the same index.
    """
    text = line.get("text") if isinstance(line.get("text"), str) else ""
    raw = line.get("textRaw") if isinstance(line.get("textRaw"), str) else ""
    if not text or not raw:
        return True
    offset = len(text) - len(raw)
    return offset >= 0 and text[offset:] == raw


def classify(original, spans, reply, fns, distance):
    """The verdict, the reason, and how far outside the markers the reply moved.

    The verdict is `accept_marker_anchored`'s. The reason names which of its
    branches produced that verdict, derived with its own helpers so the two
    cannot disagree.
    """
    blank = {"outside_segments": 0, "outside_edits": 0}
    got = fns.parse_corrected(reply)
    if got is None:
        return False, False, "unparsed", blank

    result = fns.accept(original, spans, got)
    if result["accepted"]:
        return True, True, "", blank

    split = fns.split_marked(got)
    if split is None:
        return True, False, "malformed-markers", blank
    if len(split["inside"]) != len(spans):
        return True, False, "span-count", blank

    # Everything left is a difference outside the markers. Size it: a moved
    # space and a rewritten clause both land here, and only the counts can tell
    # a reader which this was.
    expected = fns.split_marked(fns.mark_text(original, spans))
    pairs = list(zip(expected["outside"], split["outside"]))
    differing = [(a, b) for a, b in pairs if a != b]
    return (
        True,
        False,
        "outside-changed",
        {
            "outside_segments": len(differing),
            "outside_edits": sum(distance(a, b) for a, b in differing),
        },
    )


def offer_page(page, ask, fns, distance) -> list[dict]:
    """Walk one page in order, mutating it exactly as `correct_page` does.

    Returns one row per line offered. `ask(system, user)` may raise; a raising
    call is recorded as `call-failed` and the line is left alone, which is what
    the pipeline does with it.
    """
    rows: list[dict] = []
    lines = page["lines"]
    for index, line in enumerate(lines):
        spans = fns.suspect_spans(line)
        if not spans:
            continue
        original = line["text"]
        prompt = fns.build_prompt(
            fns.mark_text(original, spans),
            # Read now, not earlier: an accepted correction on the previous
            # line has already been written back into it.
            lines[index - 1]["text"] if index > 0 else "",
            lines[index + 1]["text"] if index + 1 < len(lines) else "",
        )
        started = time.time()
        try:
            reply = ask(prompt["system"], prompt["user"])
        except Exception:
            reply = None
        seconds = time.time() - started

        if reply is None:
            parsed, accepted, reason, outside = False, False, "call-failed", {
                "outside_segments": 0, "outside_edits": 0
            }
            changed_spans = changed_chars = 0
        else:
            parsed, accepted, reason, outside = classify(
                original, spans, reply, fns, distance
            )
            changed_spans = changed_chars = 0
            if accepted:
                result = fns.accept(original, spans, fns.parse_corrected(reply))
                for span, inside in zip(spans, result["insides"]):
                    if inside != span["word"]:
                        changed_spans += 1
                        changed_chars += distance(span["word"], inside)
            # Write the accepted text back, which is what makes the next
            # line's PREV context the corrected one.
            fns.apply(line, fns.parse_corrected(reply), spans)

        rows.append(
            {
                "page_id": page["page_id"],
                "book": page["book"],
                "family": page["family"],
                "correctable_index": index,
                "role": line.get("role") or "body",
                "spans": len(spans),
                "span_chars": sum(len(s["word"]) for s in spans),
                "min_conf": f"{min(s['minConf'] for s in spans):.6f}",
                "clean": int(spans_are_clean(line)),
                "parsed": int(parsed),
                "accepted": int(accepted),
                "reason": reason,
                "outside_segments": outside["outside_segments"],
                "outside_edits": outside["outside_edits"],
                "changed_spans": changed_spans,
                "changed_chars": changed_chars,
                "seconds": f"{seconds:.2f}",
            }
        )
    return rows


def read_pages(source: str, wanted: list[str], fns) -> list[dict]:
    """Load the manifest's pages, streaming each book's ndjson once."""
    by_book: dict[int, set[int]] = {}
    for page_id in wanted:
        book, page = page_id.split("-p")
        by_book.setdefault(int(book.split("-")[1]), set()).add(int(page))

    pages: list[dict] = []
    for book in sorted(by_book):
        family = json.loads(
            (Path(source) / f"book-{book}" / "calibration.json").read_text(
                encoding="utf-8"
            )
        )["family"]
        with open(
            Path(source) / f"book-{book}" / "book.ndjson", encoding="utf-8"
        ) as handle:
            for raw in handle:
                page = json.loads(raw)
                if page["page"] not in by_book[book]:
                    continue
                pages.append(
                    {
                        "page_id": f"book-{book:02d}-p{page['page']:04d}",
                        "book": book,
                        "family": family,
                        "lines": correctable(page.get("lines"), fns),
                    }
                )
        print(f"book {book:2d}: {len(pages)} pages loaded", flush=True)
    return pages


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--pipeline", required=True)
    parser.add_argument("--limit", type=int, default=0, help="stop after N pages")
    args = parser.parse_args()

    fns = load_pipeline(args.pipeline)
    from source_ocr.llm import Ollama  # noqa: E402

    import jiwer  # noqa: E402

    def distance(reference: str, hypothesis: str) -> int:
        out = jiwer.process_characters(reference or " ", hypothesis or " ")
        return out.substitutions + out.insertions + out.deletions

    ask = Ollama(timeout=300.0)
    if not ask.available():
        raise SystemExit("ollama is not answering on localhost:11434")

    with open(RUNS / "MANIFEST.csv", encoding="utf-8", newline="") as handle:
        wanted = [row["page_id"] for row in csv.DictReader(handle)]
    if args.limit:
        wanted = wanted[: args.limit]

    pages = read_pages(args.source, wanted, fns)
    jobs = sum(1 for p in pages for line in p["lines"] if fns.suspect_spans(line))
    print(
        f"\n{jobs} lines to offer over {len(pages)} pages at {WORKERS} workers",
        flush=True,
    )

    rows: list[dict] = []
    done = pages_done = 0
    started = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for produced in pool.map(
            lambda page: offer_page(page, ask, fns, distance), pages
        ):
            rows.extend(produced)
            done += len(produced)
            pages_done += 1
            if pages_done % 20 == 0:
                amortised = (time.time() - started) / max(done, 1)
                print(
                    f"{pages_done}/{len(pages)} pages, {done}/{jobs} lines  "
                    f"{amortised:.1f} s/call amortised  "
                    f"accepted {sum(r['accepted'] for r in rows)}  "
                    f"eta {(jobs - done) * amortised / 60:.0f} min",
                    flush=True,
                )

    rows.sort(key=lambda r: (r["page_id"], r["correctable_index"]))
    with open(RUNS / "VERDICTS.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    accepted = sum(r["accepted"] for r in rows)
    print(
        f"\n{len(rows)} lines offered, {accepted} accepted "
        f"({accepted / max(len(rows), 1):.1%}), {len(rows) - accepted} rejected, "
        f"in {(time.time() - started) / 60:.0f} min"
    )
    print(f"{sum(1 for r in rows if not r['clean'])} lines on the find fallback")
    reasons: dict[str, int] = {}
    for row in rows:
        if row["reason"]:
            reasons[row["reason"]] = reasons.get(row["reason"], 0) + 1
    for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {reason}: {count}")


if __name__ == "__main__":
    main()
