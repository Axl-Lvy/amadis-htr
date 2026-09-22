"""Count what the correction pass would look at, over all 24 books.

The pass only ever sees a word containing a character the recogniser scored
below `LOWCONF_THRESHOLD`, on a line whose role is body or title. How much of
the corpus that is, is a property of the recognition output alone: no LLM, no
randomness, the same answer every time. It is also E2's sampling frame, since a
page with no suspect span generates no call and can contribute no verdict.

`book.ndjson` is 3.4 GB over the 24 books and holds the transcribed text, so it
is not committed and never will be. What this writes is per page: identifiers,
role and span counts, and the lowest character confidence on the page. No text,
which is the same line `eval/freeze_ocr_runs.py` draws.

    uv run python eval/freeze_correction_reach.py "/path/to/Amadis de Gaule/ocr" \
        --pipeline /path/to/home-lab/hosts/bigpc/source_ocr_service
"""

import argparse
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data/runs/correction"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="the ocr/ directory holding book-*/")
    parser.add_argument(
        "--pipeline", required=True,
        help="source_ocr_service checkout, so the production rule is the one measured",
    )
    args = parser.parse_args()

    # The suspect-span rule is the pipeline's, imported rather than restated.
    # A copy here would be a second implementation to keep in step, and the
    # figure would stop being a measurement of the shipped system.
    sys.path.insert(0, args.pipeline)
    from source_ocr.correction import (  # noqa: E402
        CORRECTABLE_ROLES,
        LOWCONF_THRESHOLD,
        suspect_spans,
    )

    books = sorted(
        (d for d in Path(args.source).iterdir() if d.name.startswith("book-")),
        key=lambda d: int(d.name.split("-")[1]),
    )
    if not books:
        raise SystemExit(f"no book-* directories under {args.source}")

    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for book in books:
        number = int(book.name.split("-")[1])
        family = json.loads(
            (book / "calibration.json").read_text(encoding="utf-8")
        )["family"]
        with open(book / "book.ndjson", encoding="utf-8") as handle:
            for raw in handle:
                page = json.loads(raw)
                lines = page.get("lines") or []
                correctable = [
                    line
                    for line in lines
                    if (line.get("role") or "body") in CORRECTABLE_ROLES
                    and isinstance(line.get("text"), str)
                    and line["text"].strip()
                ]
                spans = [suspect_spans(line) for line in correctable]
                flat = [span for group in spans for span in group]
                rows.append(
                    {
                        "page_id": f"book-{number:02d}-p{page['page']:04d}",
                        "book": number,
                        "family": family,
                        "page": page["page"],
                        "lines": len(lines),
                        "correctable": len(correctable),
                        "lines_with_span": sum(1 for group in spans if group),
                        "spans": len(flat),
                        "min_conf": (
                            f"{min(s['minConf'] for s in flat):.6f}" if flat else ""
                        ),
                    }
                )
        print(f"book {number:2d}: {sum(1 for r in rows if r['book'] == number)} pages",
              flush=True)

    with open(OUT / "REACH.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    pages = len(rows)
    with_span = sum(1 for r in rows if r["spans"])
    print(
        f"\nthreshold {LOWCONF_THRESHOLD}: {pages:,} pages, "
        f"{sum(r['correctable'] for r in rows):,} correctable lines, "
        f"{sum(r['lines_with_span'] for r in rows):,} of them with a suspect span, "
        f"{sum(r['spans'] for r in rows):,} spans on {with_span:,} pages "
        f"({with_span / pages:.1%})"
    )


if __name__ == "__main__":
    main()
