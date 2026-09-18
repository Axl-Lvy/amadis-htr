import glob

import pytest

from amadis_htr.ground_truth import Reference, classify, read_workbook, write_csv

XLSX = glob.glob("/home/axel/Downloads/*thresors.xlsx")


def test_clean_row_is_certain():
    assert classify("Livre 1, chap 9 ") == ("certain", 1, 9)


def test_trailing_period_is_still_certain():
    assert classify("Livre 5, chap 47.") == ("certain", 5, 47)


def test_bracketed_row_is_a_conjecture():
    assert classify("[Livre 2, chap 22]") == ("conjecture", 2, 22)


def test_bracketed_and_questioned_stays_a_conjecture():
    assert classify("[Livre 3, chap 3 ?]") == ("conjecture", 3, 3)


def test_question_mark_is_uncertain():
    assert classify("Livre 2, chap 6 (?)") == ("uncertain", 2, 6)


def test_unknown_chapter_keeps_the_livre():
    assert classify("Livre 2, ?") == ("uncertain", 2, None)
    assert classify("Livre 7, chap ??") == ("uncertain", 7, None)


def test_livre_alone_is_certain_with_no_chapter():
    assert classify("Livre 8") == ("certain", 8, None)


def test_empty_and_na_carry_no_reference():
    assert classify(None) == ("none", None, None)
    assert classify("   ") == ("none", None, None)
    assert classify("N/A") == ("none", None, None)


@pytest.mark.skipif(not XLSX, reason="the source workbook is not on this machine")
def test_the_real_workbook_parses_to_the_measured_counts():
    refs = read_workbook(XLSX[0])
    assert len(refs) == 457
    assert [r.piece for r in refs] == list(range(1, 458))

    tally = {c: sum(1 for r in refs if r.confidence == c) for c in
             ("certain", "conjecture", "uncertain", "none")}
    assert tally == {"certain": 422, "conjecture": 4, "uncertain": 10, "none": 21}

    scoreable = [r for r in refs if r.confidence == "certain" and r.chapter is not None]
    assert len(scoreable) == 421


def test_write_csv_round_trips(tmp_path):
    out = tmp_path / "gt.csv"
    write_csv([Reference(1, 4, 12, "certain", "Livre 4, chap 12")], out)
    text = out.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "piece,livre,chapter,confidence,raw"
    assert "1,4,12,certain,\"Livre 4, chap 12\"" in text


@pytest.mark.skipif(not XLSX, reason="the reference workbook is not on this machine")
def test_titles_are_read_with_the_same_piece_numbering_as_the_references():
    from amadis_htr.ground_truth import read_titles

    titles = read_titles(XLSX[0])
    references = read_workbook(XLSX[0])
    assert sorted(titles) == [r.piece for r in references]
    assert all(t and not t[0].isdigit() for t in titles.values())
