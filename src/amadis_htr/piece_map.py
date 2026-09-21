"""Which Trésor piece each passage in the amadis database is.

The database dropped `Passage.number`, so nothing in it says which row of the
reference workbook a passage came from. Two import batches have to be keyed
differently, and the report keeps them apart:

- the 341 passages imported on 2026-09-14, in the workbook's own row order
  starting at piece 117. The key is position and the title is the check.
- the 118 imported on 2026-09-18 from the Juxtalinéaire catalogue, which is in
  narrative order and does not share the workbook's numbering. The key is the
  title, and a passage whose best title is not close enough stays unmapped
  rather than being guessed into a piece.
"""

import csv
import difflib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

FIRST_WORKBOOK_PIECE = 117


@dataclass(frozen=True)
class Link:
    piece: int
    passage_id: str
    cohort: str
    method: str
    similarity: float


def normalise(title: str) -> str:
    """Fold a title to the form the two catalogues can be compared in."""
    folded = unicodedata.normalize("NFKD", title.lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = folded.replace("’", "'").replace("ſ", "s")
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def similarity(left: str, right: str) -> float:
    """How close two normalised titles are, 0 to 1."""
    return difflib.SequenceMatcher(None, normalise(left), normalise(right)).ratio()


def link_by_position(
    passages: Sequence[tuple[str, str]],
    titles: Mapping[int, str],
    *,
    first_piece: int = FIRST_WORKBOOK_PIECE,
) -> list[Link]:
    """Map a batch imported in workbook order, recording each title's agreement."""
    links = []
    for offset, (passage_id, title) in enumerate(passages):
        piece = first_piece + offset
        if piece not in titles:
            raise ValueError(f"piece {piece} is past the end of the workbook")
        links.append(
            Link(
                piece=piece,
                passage_id=passage_id,
                cohort="workbook",
                method="position",
                similarity=round(similarity(title, titles[piece]), 4),
            )
        )
    return links


def link_by_title(
    passages: Sequence[tuple[str, str]],
    titles: Mapping[int, str],
    *,
    minimum: float = 0.85,
) -> tuple[list[Link], list[str]]:
    """Map a batch that shares no numbering, best title first.

    Returns the links and the ids of the passages left unmapped. A piece is
    claimed once, so a near-duplicate title cannot take a piece already taken by
    a better match.
    """
    scored = [
        (similarity(title, piece_title), passage_id, piece)
        for passage_id, title in passages
        for piece, piece_title in titles.items()
        if similarity(title, piece_title) >= minimum
    ]
    scored.sort(key=lambda row: (-row[0], row[1], row[2]))

    links: list[Link] = []
    taken_pieces: set[int] = set()
    taken_passages: set[str] = set()
    for score, passage_id, piece in scored:
        if piece in taken_pieces or passage_id in taken_passages:
            continue
        taken_pieces.add(piece)
        taken_passages.add(passage_id)
        links.append(
            Link(
                piece=piece,
                passage_id=passage_id,
                cohort="catalogue",
                method="title",
                similarity=round(score, 4),
            )
        )
    unmapped = [pid for pid, _ in passages if pid not in taken_passages]
    return sorted(links, key=lambda link: link.piece), unmapped


def write_map(links: Iterable[Link], path: str | Path) -> None:
    """Write the piece map, one row per mapped passage."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["piece", "passage_id", "cohort", "method", "title_similarity"])
        for link in sorted(links, key=lambda link: link.piece):
            writer.writerow(
                [link.piece, link.passage_id, link.cohort, link.method, link.similarity]
            )


def write_alignments(
    links: Iterable[Link],
    predictions: Mapping[str, Mapping[str, str]],
    path: str | Path,
) -> None:
    """Write the matcher's output keyed by piece, from a map and a raw export."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["piece", "cohort", "passage_id", "livre", "chapter", "start", "end", "score"]
        )
        for link in sorted(links, key=lambda link: link.piece):
            row = predictions[link.passage_id]
            writer.writerow(
                [
                    link.piece,
                    link.cohort,
                    link.passage_id,
                    row["livre"],
                    row["chapter"],
                    row["start"],
                    row["end"],
                    row["score"],
                ]
            )
