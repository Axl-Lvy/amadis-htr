import pytest

from amadis_htr.sampling import (
    Candidate,
    TrainingContaminationError,
    excluded_livres,
    sample,
    write_manifest,
)


def _candidates() -> list[Candidate]:
    out = []
    for livre, family in ((2, "A"), (4, "A"), (15, "B"), (19, "B")):
        for folio in range(1, 11):
            out.append(
                Candidate(
                    page_id=f"l{livre:02d}-f{folio:03d}",
                    livre=livre,
                    folio=str(folio),
                    family=family,
                    provenance="gallica" if livre > 2 else "bm-lyon",
                )
            )
    return out


def test_excluded_livres_reads_the_training_page_list(tmp_path):
    path = tmp_path / "training-pages.csv"
    path.write_text("page_id,livre\nx,4\ny,4\nz,3\n", encoding="utf-8")
    assert excluded_livres(path) == {3, 4}


def test_excluded_livres_refuses_a_missing_file(tmp_path):
    with pytest.raises(TrainingContaminationError):
        excluded_livres(tmp_path / "absent.csv")


def test_sampling_excludes_every_contaminated_livre():
    selected = sample(_candidates(), per_stratum=2, seed=1, excluded={4})
    assert all(c.livre != 4 for c in selected)


def test_sampling_covers_every_surviving_stratum():
    selected = sample(_candidates(), per_stratum=2, seed=1, excluded={4})
    strata = {(c.family, c.provenance) for c in selected}
    assert strata == {("A", "bm-lyon"), ("B", "gallica")}


def test_sampling_takes_per_stratum_not_in_total():
    selected = sample(_candidates(), per_stratum=3, seed=1, excluded=set())
    assert len(selected) == 3 * 3  # A/bm-lyon, A/gallica, B/gallica


def test_sampling_is_reproducible_under_a_seed():
    a = sample(_candidates(), per_stratum=3, seed=7, excluded=set())
    b = sample(_candidates(), per_stratum=3, seed=7, excluded=set())
    assert [c.page_id for c in a] == [c.page_id for c in b]


def test_a_different_seed_selects_differently():
    a = sample(_candidates(), per_stratum=3, seed=7, excluded=set())
    b = sample(_candidates(), per_stratum=3, seed=8, excluded=set())
    assert [c.page_id for c in a] != [c.page_id for c in b]


def test_a_small_stratum_yields_what_it_has_without_failing():
    thin = [c for c in _candidates() if c.livre != 15][:21]
    selected = sample(thin, per_stratum=50, seed=1, excluded=set())
    assert len(selected) == len(thin)


def test_selection_is_sorted_so_the_manifest_is_stable():
    selected = sample(_candidates(), per_stratum=3, seed=7, excluded=set())
    assert [c.page_id for c in selected] == sorted(c.page_id for c in selected)


def test_manifest_has_a_header_and_one_row_per_page(tmp_path):
    out = tmp_path / "MANIFEST.csv"
    write_manifest(sample(_candidates(), per_stratum=2, seed=1, excluded=set()), out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "page_id,livre,folio,family,provenance,stratum"
    assert len(lines) == 1 + 6
