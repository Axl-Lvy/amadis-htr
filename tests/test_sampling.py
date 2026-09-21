from amadis_htr.sampling import (
    Candidate,
    pages_the_model_saw,
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


def test_pages_the_model_saw_reads_the_training_page_list(tmp_path):
    path = tmp_path / "training-pages.csv"
    path.write_text(
        "page_id,livre,split\nx,,train\ny,,train\nz,,val\n", encoding="utf-8"
    )
    assert pages_the_model_saw(path) == {"x", "y", "z"}


def test_sampling_drops_a_page_the_model_saw():
    seen = {"l04-f001", "l04-f002"}
    selected = sample(_candidates(), per_stratum=10, seed=1, seen=seen)
    assert not (seen & {c.page_id for c in selected})


def test_sampling_samples_every_book_by_default():
    selected = sample(_candidates(), per_stratum=10, seed=1)
    assert {c.livre for c in selected} == {2, 4, 15, 19}


def test_sampling_covers_every_stratum():
    selected = sample(_candidates(), per_stratum=2, seed=1)
    strata = {(c.family, c.provenance) for c in selected}
    assert strata == {("A", "bm-lyon"), ("A", "gallica"), ("B", "gallica")}


def test_sampling_takes_per_stratum_not_in_total():
    selected = sample(_candidates(), per_stratum=3, seed=1)
    assert len(selected) == 3 * 3  # A/bm-lyon, A/gallica, B/gallica


def test_sampling_is_reproducible_under_a_seed():
    a = sample(_candidates(), per_stratum=3, seed=7)
    b = sample(_candidates(), per_stratum=3, seed=7)
    assert [c.page_id for c in a] == [c.page_id for c in b]


def test_a_different_seed_selects_differently():
    a = sample(_candidates(), per_stratum=3, seed=7)
    b = sample(_candidates(), per_stratum=3, seed=8)
    assert [c.page_id for c in a] != [c.page_id for c in b]


def test_a_small_stratum_yields_what_it_has_without_failing():
    thin = [c for c in _candidates() if c.livre != 15][:21]
    selected = sample(thin, per_stratum=50, seed=1)
    assert len(selected) == len(thin)


def test_selection_is_sorted_so_the_manifest_is_stable():
    selected = sample(_candidates(), per_stratum=3, seed=7)
    assert [c.page_id for c in selected] == sorted(c.page_id for c in selected)


def test_manifest_has_a_header_and_one_row_per_page(tmp_path):
    out = tmp_path / "MANIFEST.csv"
    write_manifest(sample(_candidates(), per_stratum=2, seed=1), out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "page_id,livre,folio,family,provenance,stratum"
    assert len(lines) == 1 + 6
