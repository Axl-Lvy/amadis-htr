from amadis_htr.fold import fold


def test_long_s_becomes_s():
    assert fold("Eſtoit") == "estoit"


def test_case_is_folded():
    assert fold("MAISTRE") == fold("maistre")


def test_u_and_v_collapse_to_v():
    assert fold("auoit") == fold("avoit") == "avoit"


def test_i_and_j_collapse_to_i():
    assert fold("Jamais") == "iamais"


def test_the_fold_is_narrower_than_the_matchers():
    # The matcher folds these together. This fold must not, because the
    # difference between them is a real recognition difference.
    assert fold("nostre") != fold("notre")
    assert fold("elle") != fold("ele")
    assert fold("troysiesme") != fold("troisiesme")


def test_whitespace_is_preserved():
    assert fold("deux mots") == "devx mots"


def test_composed_and_decomposed_accents_agree():
    assert fold("était") == fold("était")


def test_fold_is_idempotent():
    once = fold("Eſtoit Jamais AUOIT")
    assert fold(once) == once


def test_empty_string():
    assert fold("") == ""
