"""Does running the correction pass concurrently change its verdicts?

The registered design asserts that four workers change throughput and not the
verdict, on the grounds that each call is independent. That argues prompt
independence, which is not decode determinism: `Ollama` sends `temperature: 0`
and no seed, and a server batching concurrent requests can reduce in a
different order and flip a token. An assertion about the measurement's validity
should be measured.

This replays a sample of the run's own lines **sequentially**, one worker, and
compares each verdict against what the concurrent run recorded. The output is
an agreement rate the report can quote instead of an assumption.

    uv run python eval/check_correction_determinism.py \
        --source "/path/to/Amadis de Gaule/ocr" \
        --pipeline /path/to/home-lab/hosts/bigpc/source_ocr_service
"""

import argparse
import csv
import random
from pathlib import Path

from eval.run_correction import correctable, load_pipeline, offer_page, read_pages

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "data/runs/correction"

#: Enough to see a systematic difference, small enough to run sequentially in
#: under twenty minutes at the measured 18.7 s a call.
PAGES = 25
SEED = 20260922


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--pipeline", required=True)
    args = parser.parse_args()

    fns = load_pipeline(args.pipeline)
    from source_ocr.llm import Ollama  # noqa: E402

    ask = Ollama(timeout=300.0)
    if not ask.available():
        raise SystemExit("ollama is not answering on localhost:11434")

    with open(RUNS / "VERDICTS.csv", encoding="utf-8", newline="") as handle:
        first = {
            (row["page_id"], int(row["correctable_index"])): row
            for row in csv.DictReader(handle)
        }
    if not first:
        raise SystemExit("VERDICTS.csv is empty; run eval/run_correction.py first")

    # Drawn from the run's own pages, seeded, so the check is repeatable.
    page_ids = sorted({page for page, _ in first})
    chosen = random.Random(SEED).sample(page_ids, min(PAGES, len(page_ids)))
    pages = read_pages(args.source, sorted(chosen), fns)

    agree = compared = 0
    flips: list[str] = []
    for page in pages:
        for row in offer_page(page, ask, fns, lambda a, b: 0):
            key = (row["page_id"], row["correctable_index"])
            if key not in first:
                continue
            compared += 1
            before, after = first[key], row
            if (before["accepted"] == str(after["accepted"])
                    and before["reason"] == after["reason"]):
                agree += 1
            else:
                flips.append(
                    f"{key[0]}#{key[1]}: "
                    f"{before['accepted']}/{before['reason'] or 'accepted'} -> "
                    f"{after['accepted']}/{after['reason'] or 'accepted'}"
                )

    with open(
        REPO / "eval/results/correction-determinism.csv", "w",
        encoding="utf-8", newline="",
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["pages", "compared", "agree", "disagree"])
        writer.writerow([len(pages), compared, agree, compared - agree])

    print(
        f"{compared} lines replayed sequentially over {len(pages)} pages: "
        f"{agree} agree ({agree / max(compared, 1):.1%}), "
        f"{compared - agree} differ"
    )
    for flip in flips[:15]:
        print(f"  {flip}")


if __name__ == "__main__":
    main()
