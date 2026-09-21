# E2's design, registered before the run

Date: 2026-09-22
Status: written and committed **before** a single LLM reply was scored.

This file exists because E2 is the one remaining evaluation that can be run on
demand. E1, E3 and E4 wait on an annotation pass; E5 and E6 read artefacts that
already existed. E2 does not: the correction pass can be pointed at the frozen
recognition output and run again tonight, which means every choice below could
be made after seeing a number unless it is written down first. It is written
down first.

Unlike E5's gate, this is not a pass/fail criterion. The design spec already
fixes E2 as descriptive, and nothing here changes that. What is registered is
the frame, the sample, the treatment and the list of figures that will be
reported, so that the set of reported figures cannot grow to fit the result.

## The claim

**C2. LLM post-processing under a conservative accept rule.** The second pass
re-reads words carrying a character confidence below 0.6, with the suspect
spans wrapped in `⟦ ⟧`. The reply is split on the markers and accepted only
when every segment outside them is byte identical to the original. The claim is
that this rule keeps a generative model from rewriting text it was not asked to
touch — on 16th-century French, whose spelling a model's instinct is to
modernise.

## What is measured, and what is not

**Measured.** Whether each reply is accepted or rejected by the production
rule, and when rejected, which branch of the rule rejected it.

**Not measured: the CER delta.** The design spec's grid asks for correction on
against correction off, scored as a change in character error rate. That needs
a reference transcription, which is the gold set, which does not exist. E2
therefore reports what the accept rule *did* and says nothing about whether the
corrected text is closer to the truth. A rejection rate is not an accuracy, and
the report may not read one into it.

That limit is the honest one and it is stated here rather than discovered
later: E2 can show that the rule refuses bad edits, and cannot show that the
edits it accepts are improvements.

## The frame

Every page of the 24-book run frozen under `data/runs/ocr/`, restricted to
pages carrying at least one suspect span. A page with no suspect span produces
no LLM call and can carry no verdict, so including it would only dilute a rate
whose denominator is calls made.

`data/runs/correction/REACH.csv` fixes that frame, and is deterministic: it is
the production `suspect_spans` applied to the frozen recognition output, no
model and no randomness. It was computed before this file was written and
reports 14,111 pages, 435,997 correctable lines, 21,320 of them carrying a
suspect span, 23,824 spans in all, on 9,272 pages — 65.7% of the corpus.

The recognition output is uncorrected, which is what makes it a clean baseline:
all 24 books record `"wordsCorrected": 0` and `"coherenceResolved": 0`, so the
production run transcribed with both LLM passes off.

## The sample

**200 pages per type family, 400 pages, seed 20260922**, drawn by
`src/amadis_htr/sampling.py` — the same seeded stratified sampler the gold set
uses — from the pages in the frame. Every suspect line on a sampled page is
offered, so the sampled unit is the page and the analysed unit is the line.

The draw was made before this sentence was written and lands on 950 suspect
lines carrying 1,043 spans, which is the number of calls the run will make.
The size is set by what can be run and frozen in one sitting, not by a power
calculation: measured throughput is 18.7 s per call sequentially and 11.1 s at
four concurrent workers, so 920 calls is about three hours. Eight workers was
measured as *slower* than four, the GPU being saturated, so four is what the
run uses.

The manifest of selected pages is committed at
`data/runs/correction/MANIFEST.csv` before the run.

## The treatment

The production correction pass, imported and not reimplemented:
`source_ocr.correction` from the `home-lab` checkout supplies `suspect_spans`,
`mark_text`, `build_prompt`, `parse_corrected` and `accept_marker_anchored`. A
second implementation of the accept rule in this repository would make E2 a
measurement of the copy rather than of the shipped system. A test asserts the
harness's loop produces the same corrections as the pipeline's own
`correct_page` on the same input.

- model `gpt-oss:20b`, the pipeline's `DEFAULT_MODEL`, at temperature 0
- `LOWCONF_THRESHOLD = 0.6`, the pipeline's own constant
- roles `body` and `title`, the pipeline's `CORRECTABLE_ROLES`
- four concurrent workers, which changes throughput and not the verdict, since
  each call is independent and carries its own three lines of context

## The figures that will be reported, fixed here

Per type family and pooled, and no others:

1. lines offered, and spans offered
2. lines accepted, and the acceptance rate over lines offered
3. lines rejected, and the rejection rate, broken down by which branch of the
   rule rejected them: `call-failed`, `unparsed`, `malformed-markers`,
   `span-count`, `outside-changed`
4. of accepted lines, how many spans the model actually changed, and how many
   it returned untouched
5. a percentile bootstrap over pages, 10,000 resamples, 95%, on the acceptance
   rate

`outside-changed` is the branch that matters to the claim: it is the rule
catching a model that edited text it was told not to touch. The other four are
protocol failures rather than rewrites, and the report keeps them apart.

**No threshold sweep.** Lowering the threshold post hoc on the frozen verdicts
would change which spans a line carries and therefore the prompt the model saw,
so a sweep computed that way would not be the system at that threshold. What is
reported instead is the distribution of the lowest character confidence on
accepted against rejected lines, which the frozen record supports exactly.

## What is frozen, and what may not be

The verdicts are frozen at `data/runs/correction/VERDICTS.csv`, one row per
line offered, and every figure above derives from it deterministically. An LLM
reply is not reproducible, so freezing the verdict is the only way E2 reruns
anywhere the way E5 and E6 do.

**The record carries no text.** Not the line, not the marked line, not the
reply, not the corrected span. It carries identifiers, counts, confidences, the
verdict and the reason. The corpus's reuse terms are unsettled and
`LICENSE-DATA` keeps transcribed text out of this repository; a rejection
record is a fact about the rule, and it does not need the sentence to be a fact.

The consequence is recorded rather than worked around: section 7 of the report
wants a qualitative sample of rejected replies, and this repository will not
hold one. If that sample is wanted it has to be quoted in the report from a
copy held outside the repository, with the same care the corpus itself gets.
