import csv
import math
import os
import sys
from pathlib import Path

import pytest

from amadis_htr.correction import (
    FAMILIES,
    REASONS,
    REWRITE_REASON,
    Reach,
    Verdict,
    accept_rate_by_page,
    read_reach,
    read_verdicts,
    summarise_confidence,
    summarise_reach,
    summarise_reasons,
    summarise_verdicts,
    write_reach,
    write_reasons,
    write_verdicts,
)
from amadis_htr.resample import bootstrap_rate

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "data/runs/correction"

#: The pipeline lives in a private repository that CI does not check out, so
#: the equivalence test below is skipped there and runs on a machine that has
#: it. That is a real gap and it is named rather than papered over: the
#: alternative is a second implementation of the accept rule in this
#: repository, which is exactly what E2 must not measure.
PIPELINE = os.environ.get(
    "AMADIS_PIPELINE",
    str(Path.home() / "IdeaProjects/home-lab/hosts/bigpc/source_ocr_service"),
)


def _verdict(page: str, family: str = "A", accepted: bool = True, reason: str = "",
             changed: int = 1, spans: int = 1, clean: bool = True,
             edits: int = 9) -> Verdict:
    return Verdict(
        page_id=page, book=1, family=family, correctable_index=0, role="body",
        spans=spans, span_chars=8, min_conf=0.4, clean=clean, parsed=True,
        accepted=accepted, reason=reason,
        outside_segments=1 if reason == REWRITE_REASON else 0,
        outside_edits=edits if reason == REWRITE_REASON else 0,
        changed_spans=changed if accepted else 0,
        changed_chars=2 if accepted and changed else 0, seconds=1.0,
    )


def _reach(page: str, family: str = "A", spans: int = 2) -> Reach:
    return Reach(
        page_id=page, book=1, family=family, lines=40, correctable=36,
        lines_with_span=2 if spans else 0, spans=spans,
    )


def test_the_frame_covers_every_page_of_the_run():
    pages = read_reach(RUNS / "REACH.csv")
    assert len(pages) == 14111
    assert {p.family for p in pages} == set(FAMILIES)


def test_the_reach_census_agrees_with_e6_on_the_page_count():
    # Two independent walks of the same 24 books: E6 reads run.json, this reads
    # every page of book.ndjson. If they disagree, one of them is reading a
    # different corpus.
    with open(REPO / "eval/results/throughput.csv", encoding="utf-8",
              newline="") as handle:
        e6 = next(r for r in csv.DictReader(handle) if r["cohort"] == "all")
    whole = next(r for r in summarise_reach(read_reach(RUNS / "REACH.csv"))
                 if r.cohort == "all")
    assert whole.pages == int(e6["pages"])
    assert whole.books == int(e6["books"])


def test_the_families_partition_the_reach_census():
    rows = {r.cohort: r for r in summarise_reach(read_reach(RUNS / "REACH.csv"))}
    assert rows["A"].pages + rows["B"].pages == rows["all"].pages
    assert rows["A"].spans + rows["B"].spans == rows["all"].spans


def test_a_rewrite_caught_is_never_pooled_with_a_protocol_failure():
    # outside-changed is the rule catching a model that edited text it was told
    # not to touch, which is the whole of C2. The other four reasons say the
    # reply never became a candidate edit. Pooling them would let a flaky JSON
    # parser inflate the headline.
    verdicts = [
        _verdict("p1", accepted=False, reason=REWRITE_REASON),
        _verdict("p1", accepted=False, reason="unparsed"),
        _verdict("p2", accepted=False, reason="call-failed"),
        _verdict("p2", accepted=True),
    ]
    whole = next(r for r in summarise_verdicts(verdicts) if r.cohort == "all")
    assert whole.offered == 4
    assert whole.rejected == 3
    assert whole.rewrites_caught == 1
    assert whole.protocol_failures == 2
    assert whole.rewrites_caught + whole.protocol_failures == whole.rejected


def test_an_accepted_line_the_model_left_alone_is_not_an_edit():
    # A model that returns the span untouched agreed with the recogniser. That
    # is neither a rejection nor a correction, and counting it as either would
    # make the acceptance rate read as an edit rate.
    verdicts = [_verdict("p1", changed=0), _verdict("p1", changed=1)]
    whole = next(r for r in summarise_verdicts(verdicts) if r.cohort == "all")
    assert whole.accepted == 2
    assert whole.accepted_unchanged == 1
    assert whole.changed_spans == 1


def test_the_unsafe_span_path_is_counted_so_the_report_can_bound_it():
    # suspect_spans falls back to text.find when its offset check fails, and
    # that branch resolves two occurrences of one word to the same index. The
    # accept rule then compares a corrupted construction against itself and
    # accepts it, which is a hole in the property C2 is the claim about. E2
    # cannot fix it; it can say how much of the sample sat on that path.
    verdicts = [_verdict("p1", clean=False), _verdict("p1", clean=True)]
    whole = next(r for r in summarise_verdicts(verdicts) if r.cohort == "all")
    assert whole.on_find_fallback == 1


def test_a_refused_rewrite_carries_its_size():
    # "Rewrites caught" with no distance beside it cannot be defended: a moved
    # space and a rewritten clause land in the same bucket. Two totals over all
    # refusals cannot separate them either, which is what the substantial count
    # is for.
    verdicts = [
        _verdict("p1", accepted=False, reason=REWRITE_REASON, edits=9),
        _verdict("p1", accepted=False, reason=REWRITE_REASON, edits=1),
    ]
    whole = next(r for r in summarise_verdicts(verdicts) if r.cohort == "all")
    assert whole.rewrites_caught == 2
    assert whole.rewrite_edits == 10
    assert whole.rewrite_segments == 2
    # The one-character refusal is a moved space, not a rewrite.
    assert whole.rewrites_substantial == 1


def test_every_reason_gets_a_row_even_at_zero():
    # A reason the run never produced still has to appear, or a reader cannot
    # tell "never happened" from "not counted".
    rows = summarise_reasons([_verdict("p1", accepted=False, reason="unparsed")])
    assert [r.reason for r in rows] == list(REASONS)
    assert sum(r.lines for r in rows) == 1


def test_the_bootstrap_resamples_pages_and_not_lines():
    # Two pages, eight lines. Resampling lines would treat eight independent
    # draws where there are two, and report a narrower interval than the
    # evidence supports.
    by_page = accept_rate_by_page(
        [_verdict("p1") for _ in range(4)]
        + [_verdict("p2", accepted=False, reason=REWRITE_REASON) for _ in range(4)]
    )
    assert by_page == [("p1", 4, 4), ("p2", 0, 4)]
    point, low, high = bootstrap_rate(by_page, resamples=2000, seed=7)
    assert point == 0.5
    # With two pages the interval must span the whole range: every resample is
    # all of one page, all of the other, or one of each.
    assert low == 0.0 and high == 1.0


def test_an_unobserved_rate_is_not_a_measured_zero():
    # A stratum with no sampled pages has no acceptance rate. Returning 0.0
    # would put "measured 0%" and "never measured" in the same cell, and the
    # zero row would be written out as a result.
    assert all(math.isnan(x) for x in bootstrap_rate([]))


def test_summaries_round_trip_through_their_csvs(tmp_path):
    verdicts = [_verdict("p1"), _verdict("p2", family="B", accepted=False,
                                         reason=REWRITE_REASON)]
    write_reach(summarise_reach([_reach("p1"), _reach("p2", "B")]),
                tmp_path / "reach.csv")
    write_verdicts(summarise_verdicts(verdicts), tmp_path / "verdicts.csv")
    write_reasons(summarise_reasons(verdicts), tmp_path / "reasons.csv")
    for name in ("reach.csv", "verdicts.csv", "reasons.csv"):
        with open(tmp_path / name, encoding="utf-8", newline="") as handle:
            assert list(csv.DictReader(handle))


@pytest.mark.skipif(
    not Path(PIPELINE).exists(), reason="the private pipeline is not checked out"
)
def test_the_harness_offers_exactly_what_the_pipeline_would():
    # The pre-registration promises this: E2 must measure the shipped accept
    # rule, not a copy of it. `offer_page` is module level precisely so it can
    # be run head to head against the pipeline's own `correct_page`.
    #
    # The page carries three correctable lines and a header, and the scripted
    # model ECHOES the PREV it was given. That is what makes the comparison
    # meaningful: if the harness built its prompts up front instead of walking
    # the page in order, line 2 would receive an uncorrected PREV and the two
    # prompt sequences would diverge. An earlier version of this test used a
    # single line and an `ask` that ignored its arguments, and it could not
    # have caught that -- which is how the bug survived.
    import copy
    import json as _json

    sys.path.insert(0, PIPELINE)
    from source_ocr.correction import correct_page

    from eval.run_correction import correctable, load_pipeline, offer_page

    fns = load_pipeline(PIPELINE)

    def page():
        def line(ident, text, low):
            conf = [0.9] * len(text)
            for i in range(*low):
                conf[i] = 0.2
            return {
                "id": ident, "role": "body", "text": text, "textRaw": text,
                "charConfidences": conf,
            }

        return {
            "lines": [
                line("a", "et si cognoissoit le cheualier", (6, 17)),
                line("b", "qui portoit les armes vertes", (4, 11)),
                line("c", "et sen alla vers la forest", (7, 11)),
                {
                    "id": "h", "role": "header", "text": "AMADIS",
                    "textRaw": "AMADIS", "charConfidences": [0.1] * 6,
                },
            ]
        }

    seen = []

    def ask(_system, user):
        """Edit INSIDE the markers only, and record the PREV handed over.

        The edit has to be real. A model that returns the line untouched
        propagates nothing, and then a harness that built every prompt up
        front would produce the same PREV sequence as one that walks the page
        in order -- the test would pass either way. Uppercasing the marked
        span makes the accepted text differ, so line i+1's PREV is only right
        if the harness wrote line i back before building it.
        """
        payload = _json.loads(user)
        seen.append(payload["PREV"])
        out, inside = "", False
        for char in payload["LINE"]:
            if char == "\u27e6":
                inside = True
            elif char == "\u27e7":
                inside = False
            out += char.upper() if inside and char.isalpha() else char
        return _json.dumps({"corrected": out})

    theirs_page = page()
    theirs = correct_page(theirs_page, ask)
    their_prompts = list(seen)

    seen.clear()
    mine_page = page()
    rows = offer_page(
        {
            "page_id": "book-01-p0001",
            "book": 1,
            "family": "A",
            "lines": correctable(mine_page["lines"], fns),
        },
        ask,
        fns,
        lambda a, b: 0,
    )

    # The fixture has to exercise the thing it is testing: at least one line
    # must have been handed a PREV that the model had already rewritten,
    # otherwise the comparison below holds trivially.
    originals = {line["text"] for line in page()["lines"]}
    assert any(prev and prev not in originals for prev in their_prompts), (
        "no correction propagated into a later line's context, so this test "
        "cannot detect a harness that builds its prompts up front"
    )

    # Same context, line for line: the harness walked the page in order.
    assert seen == their_prompts
    # Same number of lines offered, and the header was never one of them.
    assert len(rows) == len(their_prompts)
    assert all(row["role"] == "body" for row in rows)
    assert all(entry["lineId"] != "h" for entry in theirs)
    # Same resulting text on every line, which is the accept rule agreeing.
    assert [line["text"] for line in theirs_page["lines"]] == [
        line["text"] for line in mine_page["lines"]
    ]


@pytest.mark.skipif(
    not Path(PIPELINE).exists(), reason="the private pipeline is not checked out"
)
def test_a_reply_that_edits_outside_the_markers_is_refused_and_sized():
    # The one rejection reason that is evidence for C2, and the columns that
    # make it auditable. A rejection with no distance beside it cannot be
    # defended: a moved space and a rewritten clause land in the same bucket.
    import json as _json

    from eval.run_correction import classify, load_pipeline

    fns = load_pipeline(PIPELINE)
    line = {
        "id": "a",
        "role": "body",
        "text": "et si cognoissoit le cheualier",
        "textRaw": "et si cognoissoit le cheualier",
        "charConfidences": [0.9] * 6 + [0.2] * 11 + [0.9] * 13,
    }
    spans = fns.suspect_spans(line)
    assert spans, "the fixture must produce a suspect span"

    marked = fns.mark_text(line["text"], spans)
    # The model modernises the text outside the markers, which is exactly the
    # failure the accept rule exists to refuse.
    rewritten = marked.replace("cheualier", "chevalier")
    parsed, accepted, reason, outside = classify(
        line["text"], spans, _json.dumps({"corrected": rewritten}), fns,
        lambda a, b: sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b)),
    )
    assert parsed and not accepted
    assert reason == "outside-changed"
    assert outside["outside_segments"] == 1
    assert outside["outside_edits"] > 0


def test_confidence_bands_count_refusals_and_pool_the_upper_bands():
    from dataclasses import replace

    lines = [
        replace(_verdict("p1", accepted=False, reason=REWRITE_REASON), min_conf=0.1),
        replace(_verdict("p1"), min_conf=0.2),
        replace(_verdict("p2", accepted=False, reason="parse"), min_conf=0.5),
        replace(_verdict("p2"), min_conf=0.6),
    ]
    rows = {r.band: r for r in summarise_confidence(lines, (0.0, 0.3, 0.6))}
    assert (rows["b1"].lines, rows["b1"].refused, rows["b1"].rewrites) == (2, 1, 1)
    # 0.6 sits on the top edge and must not fall out of the last band.
    assert (rows["b2"].lines, rows["b2"].refused) == (2, 1)
    assert rows["above"].lines == 2
