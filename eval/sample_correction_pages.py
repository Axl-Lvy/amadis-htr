"""E2's page set, drawn from the frozen frame and committed before the run.

The frame is `data/runs/correction/REACH.csv` restricted to pages carrying at
least one suspect span, and the draw is `src/amadis_htr/sampling.py`'s seeded
stratified sampler. Both the seed and the per-stratum size are fixed in
`docs/pre-registration/2026-09-22-e2-correction-design.md`, which was committed
before this ran.

    uv run python eval/sample_correction_pages.py
"""

import csv
from pathlib import Path

from amadis_htr.sampling import Candidate, sample, write_manifest

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "data/runs/correction"

#: Registered in the pre-registration, not chosen after seeing a result.
PER_FAMILY = 200
SEED = 20260922


def main() -> None:
    with open(RUNS / "REACH.csv", encoding="utf-8", newline="") as handle:
        frame = [
            Candidate(
                page_id=row["page_id"],
                livre=int(row["book"]),
                folio=row["page"],
                family=row["family"],
                # Recorded for four books and no others, so it is left out of
                # the stratum entirely rather than stratifying 20 books on a
                # blank. The pre-registration says family alone.
                provenance="",
            )
            for row in csv.DictReader(handle)
            if int(row["spans"]) > 0
        ]

    selected = sample(frame, per_stratum=PER_FAMILY, seed=SEED)
    write_manifest(selected, RUNS / "MANIFEST.csv")

    by_family: dict[str, int] = {}
    for candidate in selected:
        by_family[candidate.family] = by_family.get(candidate.family, 0) + 1
    print(
        f"frame {len(frame):,} pages with a suspect span; drew {len(selected)} "
        f"at seed {SEED}: " + ", ".join(f"{k} {v}" for k, v in sorted(by_family.items()))
    )


if __name__ == "__main__":
    main()
