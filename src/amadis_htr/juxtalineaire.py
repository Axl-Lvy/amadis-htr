"""Gate G1: the map between the reference workbook and the Juxtalinéaire docx.

`Juxtalinéaire pièces. Corrigé.docx` holds 460 line-diplomatic pieces and the
reference workbook holds 457. The two catalogues describe the same book in the
same order, so the difference is insertion, not reordering: the docx splits or
adds pieces the workbook does not list.

The offset is therefore a staircase, not a constant, and it is **derived here by
alignment rather than written down**. A remembered offset is exactly what the
spec's gate G1 forbids, and the one that had been remembered turned out to be
wrong: the steps fall at pieces 39, 68 and 83, not at 120.

Matching is on the title alone, scored against the opening of the docx piece. A
good many pieces are titled only `Prophetie` or `Cartel du Roy de Russie` and
run straight into the body with no header line between, so scoring the whole
docx text against such a title would reject a pairing that is in fact correct.

What this module does not do: it never copies docx text into this repository.
The docx is a corrector's unpublished labour and section 5 keeps it out. The map
carries piece numbers and a similarity score, nothing else.

One pairing is genuinely one-to-two rather than one-to-one. Workbook piece 68
merges what the docx prints as two pieces, an exhortation and its continuation,
and its title is drawn from both. The alignment picks one of them and the low
similarity on that row is the signal to a reader that it is a merge.
"""

import csv
import difflib
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping
from xml.etree import ElementTree

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_PIECE_NUMBER = re.compile(r"\d{1,3}")
_NOT_LETTERS = re.compile(r"[^a-z0-9 ]+")
_SOFT_HYPHEN = "¬"
_LONG_S = "ſ"

#: A skipped docx piece costs this much, so a single flattering coincidence
#: cannot buy an insertion the rest of the sequence does not support.
GAP_PENALTY = 0.30

#: How far past the workbook title to read, so a docx title that spells a word
#: out where the workbook abbreviates it is not truncated mid-word.
_OPENING_SLACK = 12


@dataclass(frozen=True)
class PieceMap:
    xlsx_piece: int
    docx_piece: int
    offset: int
    title_similarity: float


def read_docx_pieces(path: str | Path) -> dict[int, str]:
    """Read the docx into piece number to opening text.

    A piece opens on a paragraph that is a bare integer and runs to the next
    one. Line-end hyphens are dropped, because the compositor's break is layout
    rather than spelling and welding the halves is what makes a docx title
    comparable to the workbook's.
    """
    document = ElementTree.fromstring(
        zipfile.ZipFile(path).read("word/document.xml")
    )
    paragraphs = [
        "".join(node.text or "" for node in p.iter(_W + "t")).strip()
        for p in document.iter(_W + "p")
    ]

    opens = [
        index
        for index, text in enumerate(paragraphs)
        if _PIECE_NUMBER.fullmatch(text)
    ]

    pieces: dict[int, str] = {}
    for position, index in enumerate(opens):
        end = opens[position + 1] if position + 1 < len(opens) else len(paragraphs)
        body = " ".join(t for t in paragraphs[index + 1 : end] if t)
        pieces[int(paragraphs[index])] = body.replace(_SOFT_HYPHEN, "")
    return pieces


def title_key(text: str) -> str:
    """Normalise a title for matching only, never for scoring a transcription.

    Looser than `fold.fold`: it strips accents as well, because the workbook is
    a modern editor's catalogue and the docx is a diplomatic transcription, and
    the two disagree about accents on almost every line.
    """
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(
        c for c in decomposed if not unicodedata.combining(c)
    )
    stripped = stripped.replace(_LONG_S, "s").replace("u", "v").replace("j", "i")
    return " ".join(_NOT_LETTERS.sub(" ", stripped).split())


def title_similarity(xlsx_title: str, docx_piece: str) -> float:
    """How much of a workbook title is present at the opening of a docx piece.

    Containment rather than a symmetric ratio, because the two strings are not
    the same kind of thing: the workbook holds a title and the docx holds a
    title followed by the text. A piece titled only `Prophetie` would score 0.6
    symmetrically against its own correct pairing.
    """
    reference = title_key(xlsx_title)
    if not reference:
        return 0.0
    opening = title_key(docx_piece)[: len(reference) + _OPENING_SLACK]
    matcher = difflib.SequenceMatcher(None, reference, opening)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    return matched / len(reference)


def align(
    xlsx_titles: Mapping[int, str], docx_pieces: Mapping[int, str]
) -> list[PieceMap]:
    """Map every workbook piece onto a docx piece, in order.

    A global monotone alignment, so a local title coincidence cannot reorder the
    sequence or buy an insertion the neighbouring pieces contradict. Every
    workbook piece is mapped; extra docx pieces are skipped at `GAP_PENALTY`
    each.

    Raises ValueError when the workbook has more pieces than the docx, because
    then the two files are not the pair this gate assumes.
    """
    workbook = sorted(xlsx_titles)
    document = sorted(docx_pieces)
    if len(workbook) > len(document):
        raise ValueError(
            f"more workbook pieces ({len(workbook)}) than docx pieces "
            f"({len(document)}): these are not the two catalogues of one book"
        )

    scores = [
        [title_similarity(xlsx_titles[x], docx_pieces[d]) for d in document]
        for x in workbook
    ]

    unreachable = float("-inf")
    previous = [-GAP_PENALTY * j for j in range(len(document) + 1)]
    moves = [["skip"] * (len(document) + 1) for _ in range(len(workbook) + 1)]

    for i in range(1, len(workbook) + 1):
        current = [unreachable] * (len(document) + 1)
        for j in range(1, len(document) + 1):
            matched = (
                previous[j - 1] + scores[i - 1][j - 1]
                if previous[j - 1] > unreachable
                else unreachable
            )
            skipped = (
                current[j - 1] - GAP_PENALTY
                if current[j - 1] > unreachable
                else unreachable
            )
            current[j], moves[i][j] = (
                (matched, "match") if matched >= skipped else (skipped, "skip")
            )
        previous = current

    rows: list[PieceMap] = []
    i, j = len(workbook), len(document)
    while i > 0:
        if moves[i][j] == "match":
            x, d = workbook[i - 1], document[j - 1]
            rows.append(PieceMap(x, d, d - x, scores[i - 1][j - 1]))
            i -= 1
            j -= 1
        else:
            j -= 1
    rows.reverse()
    return rows


def write_map(rows: Iterable[PieceMap], path: str | Path) -> None:
    """Write the map, one row per workbook piece."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["xlsx_piece", "docx_piece", "offset", "title_similarity"])
        for row in rows:
            writer.writerow(
                [
                    row.xlsx_piece,
                    row.docx_piece,
                    row.offset,
                    f"{row.title_similarity:.3f}",
                ]
            )
