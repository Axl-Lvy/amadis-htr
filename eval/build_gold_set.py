"""Build the gold set from the Transkribus exports, and record why each page is in.

The exports hold every page of a document, corrected or not, trained on or not.
This keeps the pages a human corrected and the model never read, copies their
PAGE XML into `data/gold/transcriptions/`, and writes `data/gold/MANIFEST.csv`
with one row per candidate page — kept or refused, and for the refused ones, why.

No page image is copied. Reuse terms differ per holding institution and are
unsettled for at least one, so the manifest records the holder per page and the
images stay where they are. The transcriptions are editorial work and are
committed under LICENSE-DATA.

The exports are not committed. They are Transkribus's own artefact, they carry
the uncorrected pages too, and re-exporting the same documents reproduces them.
What is committed is the subset that gets scored and the manifest that justifies
it, which is the same line `eval/freeze_ocr_runs.py` draws.

    uv run python eval/build_gold_set.py ~/amadis-artefacts/transkribus
"""

import argparse
import csv
import shutil
from pathlib import Path

from amadis_htr.gold import read_exclusions, read_pages, select
from amadis_htr.sampling import pages_the_model_saw

REPO = Path(__file__).resolve().parent.parent
GOLD = REPO / "data/gold"
SPLITS = GOLD / "splits"

#: The holding institution per Transkribus document, for LICENSE-DATA's note on
#: page images. Recorded here rather than read from the export, because the
#: export states it only inside a free-text title.
HOLDING = {
    "10925942": "BM Lyon (numelyo)",
    "10926025": "BM Lyon (numelyo)",
}

WORK = {
    "10925942": "Trésor des Amadis T. 1",
    "10926025": "Trésor des Amadis T. 2",
    "16583795": "Amadis de Gaule, livre 13 (extrait)",
}

FIELDS = [
    "page_id",
    "doc_id",
    "page_nr",
    "work",
    "holding",
    "status",
    "last_change",
    "seeded_by",
    "lines",
    "chars",
    "words",
    "kept",
    "reason",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source", help="directory holding the unpacked exports, <docId>/<title>/page/"
    )
    args = parser.parse_args()

    trained_on = pages_the_model_saw(SPLITS / "training-pages.csv")
    excluded = read_exclusions(SPLITS / "excluded-pages.csv")

    directories = sorted(Path(args.source).glob("*/*/*/page"))
    directories += sorted(Path(args.source).glob("*/*/page"))
    if not directories:
        raise SystemExit(f"no exported page/ directories under {args.source}")

    candidates = [page for directory in directories for page in read_pages(directory)]
    verdicts = select(candidates, trained_on=trained_on, excluded=excluded)

    pages_dir = GOLD / "transcriptions"
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    pages_dir.mkdir(parents=True)

    by_path = {}
    for directory in directories:
        for path in directory.glob("*.xml"):
            by_path[f"{path.parent.parent.parent.name}_{path.stem}"] = path

    with open(GOLD / "MANIFEST.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for page, reason in verdicts:
            writer.writerow(
                {
                    "page_id": page.page_id,
                    "doc_id": page.doc_id,
                    "page_nr": page.page_nr,
                    "work": WORK.get(page.doc_id, ""),
                    "holding": HOLDING.get(page.doc_id, ""),
                    "status": page.status,
                    "last_change": page.last_change[:10],
                    "seeded_by": page.seeded_by,
                    "lines": len(page.lines),
                    "chars": page.chars,
                    "words": page.words,
                    "kept": "yes" if reason is None else "no",
                    "reason": reason or "",
                }
            )
            if reason is None:
                shutil.copy2(by_path[page.page_id], pages_dir / f"{page.page_id}.xml")

    kept = [page for page, reason in verdicts if reason is None]
    refused: dict[str, int] = {}
    for _, reason in verdicts:
        if reason is not None:
            refused[reason] = refused.get(reason, 0) + 1

    seeds = sorted({page.seeded_by for page in kept})
    print(
        f"{len(candidates):,} candidate pages; kept {len(kept)} "
        f"over {len({p.doc_id for p in kept})} documents, "
        f"{sum(len(p.lines) for p in kept):,} lines, "
        f"{sum(p.chars for p in kept):,} characters"
    )
    print("refused: " + ", ".join(f"{k} {v}" for k, v in sorted(refused.items())))
    print("seeded by model_id " + ", ".join(seeds) + " — the reference is post-edited")


if __name__ == "__main__":
    main()
