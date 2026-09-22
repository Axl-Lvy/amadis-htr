import csv
from pathlib import Path

import pytest

from amadis_htr.gold import (
    CORRECTED,
    GoldPage,
    read_exclusions,
    read_page,
    read_pages,
    refusal,
    select,
)
from amadis_htr.sampling import pages_the_model_saw

REPO = Path(__file__).resolve().parent.parent
GOLD = REPO / "data/gold"
PAGES = GOLD / "transcriptions"
MANIFEST = GOLD / "MANIFEST.csv"
TRAINING = GOLD / "splits/training-pages.csv"
EXCLUDED = GOLD / "splits/excluded-pages.csv"

PAGE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PcGts xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15">
    <Metadata>
        <Creator>prov=READ-COOP:name=PyLaia@TranskribusPlatform:version=2.51.0:model_id=581889:lm=none:date=09_09_2026_14:32</Creator>
        <Created>2025-09-29T22:45:02.867+02:00</Created>
        <LastChange>2026-09-16T11:07:10.385+02:00</LastChange>
        <TranskribusMetadata docId="10925942" pageNr="50" status="{status}"/>
    </Metadata>
    <Page imageFilename="0050_p050.jpg" imageWidth="2479" imageHeight="3508">
        <TextRegion id="tr_1">
            <TextLine id="tr_1_tl_3" custom="readingOrder {{index:1;}}">
                <TextEquiv><Unicode>seconde ligne</Unicode></TextEquiv>
            </TextLine>
            <TextLine id="tr_1_tl_2" custom="readingOrder {{index:0;}}">
                <TextEquiv><Unicode>premiere ligne</Unicode></TextEquiv>
            </TextLine>
            <TextLine id="tr_1_tl_4" custom="readingOrder {{index:2;}}">
                <TextEquiv><Unicode/></TextEquiv>
            </TextLine>
        </TextRegion>
    </Page>
</PcGts>
"""


def _write(tmp_path: Path, name: str = "0050_p050.xml", status: str = CORRECTED) -> Path:
    path = tmp_path / name
    path.write_text(PAGE_XML.format(status=status), encoding="utf-8")
    return path


def _page(page_id: str, *, status: str = CORRECTED, lines=("a",)) -> GoldPage:
    return GoldPage(
        page_id=page_id,
        doc_id=page_id.split("_")[0],
        page_nr=1,
        status=status,
        last_change="2026-09-16",
        seeded_by="581889",
        lines=tuple(lines),
    )


def test_lines_come_back_in_reading_order_not_document_order(tmp_path):
    page = read_page(_write(tmp_path))
    # The file lists index 1 before index 0, so document order would invert them.
    assert page.lines == ("premiere ligne", "seconde ligne")


def test_an_empty_unicode_element_is_not_a_line(tmp_path):
    assert len(read_page(_write(tmp_path)).lines) == 2


def test_the_page_id_carries_the_document_so_the_work_stays_checkable(tmp_path):
    page = read_page(_write(tmp_path))
    assert page.page_id == "10925942_0050_p050"
    assert page.doc_id == "10925942"
    assert page.page_nr == 50


def test_the_seed_model_is_recorded_because_the_reference_is_post_edited(tmp_path):
    assert read_page(_write(tmp_path)).seeded_by == "581889"


def test_chars_counts_the_line_join_the_way_the_scorer_does(tmp_path):
    page = read_page(_write(tmp_path))
    # "premiere ligne seconde ligne" — one space where the line break was.
    assert page.chars == len("premiere ligne seconde ligne")
    assert page.words == 4


def test_a_page_the_model_read_is_refused_however_well_corrected():
    page = _page("10925942_0111_p111")
    assert refusal(page, trained_on={page.page_id}, excluded={}) == "trained-on"


def test_an_uncorrected_page_is_refused():
    page = _page("10925942_0500_p500", status="IN_PROGRESS")
    assert refusal(page, trained_on=set(), excluded={}) == "not-corrected"


def test_an_excluded_page_is_refused_with_the_reason_it_was_given():
    page = _page("10925942_0015_p015")
    excluded = {page.page_id: "front-matter"}
    assert refusal(page, trained_on=set(), excluded=excluded) == "front-matter"


def test_training_beats_exclusion_so_the_reason_survives_a_change_of_frame():
    page = _page("10925942_0015_p015")
    reason = refusal(
        page, trained_on={page.page_id}, excluded={page.page_id: "front-matter"}
    )
    assert reason == "trained-on"


def test_a_corrected_unseen_page_is_kept():
    page = _page("16583795_0001_p001")
    assert refusal(page, trained_on=set(), excluded={}) is None


def test_select_reports_refused_pages_rather_than_dropping_them():
    pages = [_page("10925942_0111_p111"), _page("16583795_0001_p001")]
    verdicts = select(pages, trained_on={"10925942_0111_p111"}, excluded={})
    assert [reason for _, reason in verdicts] == ["trained-on", None]


# --- the committed set itself -------------------------------------------------


def _manifest() -> list[dict]:
    with open(MANIFEST, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_every_kept_page_has_its_page_xml_committed_and_no_others():
    kept = {row["page_id"] for row in _manifest() if row["kept"] == "yes"}
    assert {path.stem for path in PAGES.glob("*.xml")} == kept
    assert len(kept) == 118


def test_no_gold_page_is_a_page_the_model_trained_on():
    trained = pages_the_model_saw(TRAINING)
    kept = {row["page_id"] for row in _manifest() if row["kept"] == "yes"}
    assert kept & trained == set()


def test_every_kept_page_is_corrected_and_carries_text():
    for page in read_pages(PAGES):
        assert page.status == CORRECTED
        assert page.lines


def test_every_refused_page_states_a_reason_and_every_kept_one_states_none():
    for row in _manifest():
        assert bool(row["reason"]) == (row["kept"] == "no")


def test_every_exclusion_named_in_the_split_appears_refused_in_the_manifest():
    excluded = read_exclusions(EXCLUDED)
    refused = {row["page_id"]: row["reason"] for row in _manifest() if row["kept"] == "no"}
    for page_id, reason in excluded.items():
        assert refused[page_id] == reason


def test_the_manifest_records_the_seed_model_for_every_kept_page():
    # Without this column the post-editing bias is an assertion in prose only.
    for row in _manifest():
        if row["kept"] == "yes":
            assert row["seeded_by"]


def test_the_gold_set_spans_both_works_and_says_which_is_which():
    works = {row["work"] for row in _manifest() if row["kept"] == "yes"}
    assert works == {"Trésor des Amadis T. 1", "Amadis de Gaule, livre 13 (extrait)"}


@pytest.mark.parametrize("field", ["doc_id", "page_nr", "lines", "chars", "words"])
def test_the_manifest_is_populated(field):
    assert all(row[field] for row in _manifest())
