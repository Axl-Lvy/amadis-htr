import pytest

from amadis_htr.piece_map import (
    Link,
    link_by_position,
    link_by_title,
    normalise,
    similarity,
    write_alignments,
    write_map,
)


def test_normalise_folds_case_accents_and_the_long_s():
    assert normalise("La Harangue du Damoiſel") == "la harangue du damoisel"
    assert normalise("Réponſe d’Amadis, à luy") == "reponse d amadis a luy"


def test_similarity_is_one_for_the_same_title_written_differently():
    assert similarity("Harangue d’Amadis", "harangue d'amadis") == 1.0


def test_link_by_position_walks_the_workbook_from_its_first_piece():
    titles = {117: "Complainte", 118: "Exhortation", 119: "Response"}
    links = link_by_position([("a", "Complainte"), ("b", "Exhortation")], titles)
    assert [(l.piece, l.passage_id) for l in links] == [(117, "a"), (118, "b")]
    assert all(l.method == "position" for l in links)


def test_link_by_position_records_a_title_that_disagrees():
    titles = {117: "Complainte de la royne", 118: "Exhortation de Mabile"}
    links = link_by_position([("a", "Complainte de la royne"), ("b", "Autre chose")], titles)
    assert links[0].similarity == 1.0
    assert links[1].similarity < 0.5


def test_link_by_position_refuses_to_run_past_the_workbook():
    with pytest.raises(ValueError):
        link_by_position([("a", "x"), ("b", "y")], {117: "x"})


def test_link_by_title_takes_the_best_match_and_claims_a_piece_once():
    titles = {1: "La harangue du damoisel", 2: "La harangue de Lisuart"}
    passages = [("p1", "La harangue du damoisel"), ("p2", "La harangue du damoisel de la mer")]
    links, unmapped = link_by_title(passages, titles, minimum=0.6)
    assert [(l.piece, l.passage_id) for l in links] == [(1, "p1"), (2, "p2")]
    assert unmapped == []


def test_link_by_title_leaves_a_passage_unmapped_below_the_minimum():
    links, unmapped = link_by_title([("p1", "quelque chose")], {1: "tout autre"}, minimum=0.85)
    assert links == []
    assert unmapped == ["p1"]


def test_write_map_has_a_header_and_one_row_per_link(tmp_path):
    out = tmp_path / "piece-map.csv"
    write_map([Link(118, "b", "workbook", "position", 1.0), Link(117, "a", "workbook", "position", 0.9)], out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "piece,passage_id,cohort,method,title_similarity"
    assert lines[1].startswith("117,a,")
    assert len(lines) == 3


def test_write_alignments_joins_the_map_to_the_raw_export(tmp_path):
    out = tmp_path / "alignments.csv"
    predictions = {
        "a": {"livre": "4", "chapter": "12", "start": "100", "end": "200", "score": "0.91"}
    }
    write_alignments([Link(117, "a", "workbook", "position", 1.0)], predictions, out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "piece,cohort,passage_id,livre,chapter,start,end,score"
    assert lines[1] == "117,workbook,a,4,12,100,200,0.91"
