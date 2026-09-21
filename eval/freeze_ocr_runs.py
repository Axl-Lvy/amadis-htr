"""Vendor the OCR harness's own run records into `data/runs/ocr/`.

The 24 books were transcribed on the big PC against a GPU and a fine-tuned
model. Rerunning that needs the corpus, the model and the hardware; scoring it
needs neither, so the harness's records are frozen here and E6 reads them from
the repository like every other evaluation.

Only the records are vendored, never the page images or the transcriptions:
the records hold counts, timings and structural anomalies, and nothing of the
text whose reuse terms are unsettled. The four fields holding an absolute path
are reduced to basenames by `sanitise.scrub_run_paths`.

    uv run python eval/freeze_ocr_runs.py "/path/to/Amadis de Gaule/ocr"
"""

import csv
import json
import sys
from pathlib import Path

from amadis_htr.sanitise import scrub_run_paths

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data/runs/ocr"
RECORDS = ("run.json", "calibration.json")


def main(source: str) -> None:
    books = sorted(
        (d for d in Path(source).iterdir() if d.name.startswith("book-")),
        key=lambda d: int(d.name.split("-")[1]),
    )
    if not books:
        raise SystemExit(f"no book-* directories under {source}")

    index: list[dict[str, object]] = []
    for book in books:
        target = OUT / book.name
        target.mkdir(parents=True, exist_ok=True)
        records = {}
        for name in RECORDS:
            record = json.loads((book / name).read_text(encoding="utf-8"))
            record = scrub_run_paths(record)
            # sort_keys so a re-freeze of unchanged input is an empty diff.
            (target / name).write_text(
                json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )
            records[name] = record

        run, calibration = records["run.json"], records["calibration.json"]
        index.append(
            {
                "system": "ocr",
                "book": calibration["book"],
                "family": calibration["family"],
                "source": run["input"],
                "model": run["model"],
                "device": run["device"],
                "workers": run["workers"],
                "working_width": run["workingWidth"],
                "pages": run["pagesRun"],
                "seconds": run["seconds"],
            }
        )

    with open(OUT / "INDEX.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(index[0]))
        writer.writeheader()
        writer.writerows(index)

    print(f"{len(index)} books frozen under {OUT.relative_to(REPO)}")
    print(f"{sum(r['pages'] for r in index):,} pages, "
          f"{sum(r['seconds'] for r in index) / 3600:.2f} hours")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
