"""Regenerate `data/localisation/juxtalineaire-map.csv` from the two source files.

Neither source file is in this repository. The workbook is the editor's
catalogue and the docx is a corrector's unpublished transcription, so both stay
outside and only the derived map is committed. Run this with their paths when
the map has to be rebuilt:

    uv run python eval/derive_juxtalineaire_map.py <workbook.xlsx> <pieces.docx>
"""

import sys
from pathlib import Path

from amadis_htr.ground_truth import read_titles
from amadis_htr.juxtalineaire import align, read_docx_pieces, write_map

OUT = Path(__file__).resolve().parent.parent / "data/localisation/juxtalineaire-map.csv"


def main(workbook: str, docx: str) -> None:
    rows = align(read_titles(workbook), read_docx_pieces(docx))
    write_map(rows, OUT)

    steps = []
    previous = None
    for row in rows:
        if row.offset != previous:
            steps.append(f"{row.xlsx_piece}:+{row.offset}")
            previous = row.offset
    mean = sum(r.title_similarity for r in rows) / len(rows)
    weak = [r.xlsx_piece for r in rows if r.title_similarity < 0.75]
    print(f"{len(rows)} pieces mapped, mean title containment {mean:.3f}")
    print(f"offset steps at piece:offset {' '.join(steps)}")
    print(f"below 0.75, read these by hand: {weak}")
    print(f"written to {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
