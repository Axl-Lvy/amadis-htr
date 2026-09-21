import csv
import zipfile

import pytest

from amadis_htr.juxtalineaire import (
    PieceMap,
    align,
    read_docx_pieces,
    title_key,
    title_similarity,
    write_map,
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx(tmp_path, paragraphs):
    """Build the smallest .docx this parser has to read.

    The real file is not in this repository: it is a corrector's unpublished
    labour and section 5 keeps it out. Every parser test therefore runs on a
    synthetic document built here.
    """
    body = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{p}</w:t></w:r></w:p>'
        for p in paragraphs
    )
    path = tmp_path / "pieces.docx"
    with zipfile.ZipFile(path, "w") as handle:
        handle.writestr(
            "word/document.xml",
            f'<?xml version="1.0"?><w:document xmlns:w="{W}"><w:body>{body}'
            "</w:body></w:document>",
        )
    return path


def test_a_bare_integer_paragraph_opens_a_piece(tmp_path):
    path = _docx(tmp_path, ["1", "La harangue du Damoysel", "Au premier livre.", "Mes compagnons", "", "2", "Autre harangue", "Au mesme CHAP."])
    assert read_docx_pieces(path) == {
        1: "La harangue du Damoysel Au premier livre. Mes compagnons",
        2: "Autre harangue Au mesme CHAP.",
    }


def test_a_line_end_hyphen_is_removed_not_kept(tmp_path):
    # The compositor's break is layout, not spelling, and welding the halves is
    # what makes the docx title comparable to the workbook's.
    path = _docx(tmp_path, ["1", "aux Sol¬", "datz Gaulois"])
    assert read_docx_pieces(path) == {1: "aux Sol datz Gaulois"}


def test_a_number_inside_a_sentence_does_not_open_a_piece(tmp_path):
    path = _docx(tmp_path, ["1", "Harangue", "chapitre 12 du livre"])
    assert list(read_docx_pieces(path)) == [1]


def test_the_title_key_strips_accents_the_declared_fold_keeps():
    # `fold.fold` is the evaluation's normalisation and deliberately keeps
    # accents. Matching a modernised catalogue title against a diplomatic
    # transcription needs a looser key, so this one is local and separate.
    assert title_key("déconneuë") == title_key("deconneue")
    assert title_key("Harengue d'Arquisil") == "harengve d arqvisil"


def test_similarity_scores_the_opening_not_the_whole_piece():
    # Several pieces are titled only "Prophetie" and run straight into the body.
    # Scoring the full docx text against that title would score near zero on a
    # pairing that is in fact correct.
    short = "Prophetie"
    piece = "Prophetie. Quand l'ours matin sailly de la forest Russiane, foudroyera"
    assert title_similarity(short, piece) > 0.9


def test_alignment_recovers_an_inserted_piece():
    xlsx = {1: "Premiere harangue", 2: "Response du Roi", 3: "Complainte d'Oriane"}
    docx = {
        1: "Premiere harangue Au premier livre",
        2: "Prophetie d'Urgande, toute autre chose",
        3: "Response du Roi Au mesme CHAP",
        4: "Complainte d'Oriane Au mesme CHAP",
    }
    rows = align(xlsx, docx)
    assert [(r.xlsx_piece, r.docx_piece, r.offset) for r in rows] == [
        (1, 1, 0),
        (2, 3, 1),
        (3, 4, 1),
    ]


def test_alignment_maps_every_workbook_piece():
    xlsx = {n: f"Harangue numero {n}" for n in range(1, 21)}
    docx = {n: f"Harangue numero {n} Au mesme CHAP" for n in range(1, 21)}
    rows = align(xlsx, docx)
    assert [r.xlsx_piece for r in rows] == sorted(xlsx)
    assert all(r.offset == 0 for r in rows)


def test_alignment_is_monotone_so_pieces_never_cross():
    # A local title coincidence must not be able to reorder the sequence: the
    # two catalogues describe the same book in the same order.
    xlsx = {1: "Response du Roi", 2: "Harangue d'Amadis", 3: "Response du Roi"}
    docx = {
        1: "Response du Roi a ladite harengue",
        2: "Harangue d'Amadis a ses compagnons",
        3: "Response du Roi sur le mesme propos",
    }
    rows = align(xlsx, docx)
    numbers = [r.docx_piece for r in rows]
    assert numbers == sorted(numbers)


def test_a_weak_pairing_keeps_its_similarity_rather_than_being_dropped():
    # Gate G1 needs to see which rows are shaky. Silently dropping them would
    # make the map look cleaner than the evidence is.
    xlsx = {1: "Premiere harangue", 2: "Titre que rien ne rapproche"}
    docx = {1: "Premiere harangue Au premier livre", 2: "Zzzz qqqq wwww xxxx"}
    rows = align(xlsx, docx)
    assert len(rows) == 2
    assert rows[1].title_similarity < 0.4


def test_write_map_creates_its_own_output_directory(tmp_path):
    out = tmp_path / "localisation" / "juxtalineaire-map.csv"
    write_map([PieceMap(1, 1, 0, 0.98)], out)
    with open(out, encoding="utf-8", newline="") as handle:
        assert list(csv.DictReader(handle)) == [
            {
                "xlsx_piece": "1",
                "docx_piece": "1",
                "offset": "0",
                "title_similarity": "0.980",
            }
        ]


def test_no_docx_text_reaches_the_map(tmp_path):
    # Section 5 keeps the corrector's transcription out of this public
    # repository. The map carries numbers and a score, never a title.
    out = tmp_path / "map.csv"
    write_map([PieceMap(1, 1, 0, 0.98)], out)
    assert "harangue" not in out.read_text(encoding="utf-8").lower()


def test_alignment_refuses_a_workbook_longer_than_the_docx():
    with pytest.raises(ValueError, match="more workbook pieces"):
        align({1: "a", 2: "b", 3: "c"}, {1: "a"})


def test_the_committed_map_still_says_what_the_spec_says_it_says():
    """The staircase is stated in prose in three places. This is the source.

    The spec, the README and the report all copy this table by hand, which is
    exactly the thing rule 1 of the architecture forbids. Until those tables are
    generated, this test is what keeps them honest.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    with open(root / "data/localisation/juxtalineaire-map.csv", encoding="utf-8", newline="") as handle:
        rows = [
            (int(r["xlsx_piece"]), int(r["docx_piece"]), int(r["offset"]))
            for r in csv.DictReader(handle)
        ]

    assert len(rows) == 457
    assert [x for x, _, _ in rows] == list(range(1, 458))
    assert [d for _, d, _ in rows] == sorted(d for _, d, _ in rows)
    assert sorted(set(range(1, 461)) - {d for _, d, _ in rows}) == [39, 69, 85]

    blocks: list[tuple[int, int, int]] = []
    for xlsx, _, offset in rows:
        if blocks and blocks[-1][2] == offset:
            blocks[-1] = (blocks[-1][0], xlsx, offset)
        else:
            blocks.append((xlsx, xlsx, offset))
    assert blocks == [(1, 38, 0), (39, 67, 1), (68, 82, 2), (83, 457, 3)]
