# amadis-htr: the report's outline, section by section

Date: 2026-09-20
Status: drafted 2026-09-20 under the autonomy grant, awaiting review
Extends: section 12 of `docs/specs/2026-09-18-amadis-htr-report-design.md`, which
fixes the nine-section skeleton. Follows that spec's 2026-09-21 decision that both
works are the target domain, so nothing here is framed as in domain or out of domain
and E1 reports one CER per work. This file keeps that skeleton and says what each
section contains, what it reads, and what it may not say.

**The report cannot be written today.** E1 to E5 are unmeasured, no LaTeX engine is
installed, and `eval/results/` is empty apart from the localisation reference. Six of
the nine sections can be drafted now against material that exists. Section 6 cannot,
and section 7 depends on it. Each section below carries its status.

## Open decisions, with the default taken if nothing overrides it

| decision | default | why it is a default and not a fact |
|---|---|---|
| language | English | fixed by the design spec's deliverable line |
| length | 25 to 26 pages of body, references and appendices on top | no page limit is recorded anywhere. A data science project report of this scope sits between 20 and 30 |
| document class | `scrartcl` with `fontspec`, LuaLaTeX | the spec fixes the engine and the Unicode requirement, not the class |
| citation style | `biblatex` numeric with `biber` | the spec fixes the tooling. Numeric keeps a 25-page report's citations out of the way |
| anonymity | none, the repository is public under the user's name | the spec plans a public repository and a Hugging Face card |

## IMRaD, mapped onto the nine sections

The report is an empirical evaluation, so it follows IMRaD moves inside the spec's
own section numbering rather than renaming anything.

| IMRaD | sections | the move it has to make |
|---|---|---|
| Introduction | 1, 2 | motivating problem, state of the field, the gap, this work as the answer |
| Methods | 3, 4, 5 | corpus, system under test, protocol, in enough detail to repeat |
| Results | 6 | findings only, no interpretation |
| Discussion | 7, 8, 9 | explain the findings, compare them to the literature, bound them, conclude |

**Four additions to section 12's list**, since a graded report needs them and the
skeleton does not name them: an abstract before section 1, a references section after
section 9, appendices after that, and an explicit home for the compare-to-literature
move. That move lives at the head of section 7, where the measured error profile is
set against what section 2 reported for CATMuS, Transkribus and LLM post-correction.
Section 9 states implications and does not re-argue them.

---

## Abstract

**Purpose.** One paragraph a reader can stop at.

**Content.** The corpus and why it is hard, in two sentences. The system in one. The
three claims and the headline number for each, the *Amadis de Gaule* CER for C1, the
marker-anchor rejection rate for C2, Livre and chapter accuracy for C3. One sentence
on what the evaluation cost, meaning the gold set's size and its single annotator. One
sentence on the released artefacts.

**Inputs.** `report/generated/macros.tex` only. Written last.

**Status.** Blocked on section 6.

**Not here.** Method detail, related work, any number that is not also in section 6.

## 1. Introduction

**Purpose.** Establish that a production system with no measurement is the problem, and
that this report is the measurement.

**Content.** The two corpora and the philological question the digitisation serves,
1,770 chapters of *Amadis de Gaule* and the *Trésor* anthologies that extract from
them. Why off-the-shelf OCR fails on 16th-century French print: long `ſ`, bâtarde type,
drop caps, running heads and catchwords, folio numbering in two systems, three scan
provenances of uneven quality. What exists today, which is one validation CER on a 10%
page-level split of a single volume, and what that number cannot support. The gap, in
the spec's own terms: no figure of any kind for *Amadis de Gaule*, no WER, no
measured baseline, no
evaluation of either LLM pass, and structural figures the pipeline computes and
discards. The three claims as the answer, one paragraph each, and a forward reference
to the section that evaluates each.

**Inputs.** Design spec sections 1 and 2. Corpus counts from section 3's sources. No
`eval/results/` dependency.

**Status.** Writable now.

**Not here.** Results. System mechanics. Anything that reads as a defence of the
engineering.

## 2. Related work

**Purpose.** Place the three claims against published work, and give section 7 its
comparison anchors.

**Content.** Four threads. Early-modern print recognition and the CATMuS family,
including what CATMuS-Print [Large] was trained on and why it is the right base.
kraken as the engine, version 7.0.2, and what it ships and does not ship, which is why
E1's independent comparator has to be a chosen published model rather than a default.
Transkribus as the annotation platform and as a commercial baseline, with its models
opaque. LLM post-correction of OCR, where the literature's usual failure mode is
fluent rewriting, which is exactly what C2's accept rule defends against. Close with the question the search has to answer: has anyone published a CER for a
CATMuS-Print fine-tune on a 16th-century French romance corpus of this size? The
novelty claim is made only if the search comes back empty, and the search is
recorded.

**Inputs.** `report/refs.bib`, to be acquired. Nothing generated.

**Status.** Writable now, once the bibliography exists.

**Not here.** A survey. Four threads, roughly two paragraphs each.

## 3. The corpus

**Purpose.** Describe the material precisely enough that the evaluation's strata make
sense, and establish that both works are one target domain rather than two.

**Content.** Two editions and their type families, books 1 to 12 in large folio bâtarde
with roman folio numbers against books 13 to 24 in smaller clean roman with italic
rubrics and arabic numbers. Three scan provenances: bitonal 600 dpi TIFF from BM Lyon,
greyscale Gallica PDF, and the stamped Biblioteca Valenciana copy. The *Trésor*
anthologies and their relation to the baseline text, which is what makes C3 a retrieval
problem. The numbers: 3,646,003 word tokens of baseline text, 1,770 chapters, 24 books,
457 pieces in the localisation reference of which 422 carry a certain assignment. The
training corpus as a subset of all this, 487 *Trésor* T.1 pages and 13,997 lines.

**Inputs.** `data/localisation/ground-truth.csv` for the piece counts, the recovery
note for the training-corpus counts, `data/gold/splits/training-pages.csv` for the page
list. Figures: one plate showing one page per type family, if the scan reuse terms
allow it.

**Status.** Writable now, except the plate.

**Not here.** Sampling. That is section 5.

## 4. System

**Purpose.** Explain the system well enough that the results are interpretable, and
stop there.

**Content.** Recognition: the base model, the fine-tune's two configurations, and the
shipped artefact identified by hash. Layout: the geometric rules, roles, reading order,
and the ambiguity that E3 scores, in one compressed subsection. The two LLM passes: the
coherence pass and the low-confidence pass, with the accept rule stated in full because
it is C2's substance. Localisation: the period-aware normaliser, the rare-word seed
index at `length >= 6` and document frequency `<= 200`, and per-book anchor chaining.
One paragraph on orchestration and the CPU/GPU fork, no more. A table of every
threshold the system contains, its value, where it came from and whether this report
calibrates it: `LOWCONF_THRESHOLD` 0.6, `OCR_DROPCAP_MIN_PROB` 0.6, `MIN_SCORE` 0.808,
`MIN_SEED_LENGTH` 6, `MAX_SEED_DF` 200, `UNCERTAIN` 0.85.

**Inputs.** `pipeline/` snapshot, `PROVENANCE.md`, the design spec sections 2 and 3.
One figure: the pipeline as a data-flow diagram, hand-specified in TikZ, no screenshot.

**Status.** Writable now.

**Not here.** The non-goals of spec section 3 expanded into a manual. Every subsection
here is capped, and the cap is the page budget below.

## 5. Evaluation protocol

**Purpose.** Let a reader repeat the evaluation, and let them see the decisions were
made before the numbers.

**Content.** The gold set: frame, strata, the seeded sampler, the 20-page target, the
exclusions and why front matter and woodcut pages are out. The frame is all 24 books
of *Amadis de Gaule* minus the pages the model trained on, which is the only exclusion
left and which currently removes nothing. The annotation convention,
`data/gold/GUIDELINES.md`, written before annotating. Single annotator, with blind
re-annotation of three pages after a week as the noise floor, and the rule that a
difference below it is not claimed. The fold, defined once, applied identically to
hypothesis and reference, and why every E1 figure is reported raw and folded. The
metrics: CER and WER, whitespace counted, line breaks normalised to one space,
character-weighted aggregation, bootstrap intervals over pages at 10,000 resamples. The
training split as a stated fact rather than an assertion: it was re-derived and
verified against the compiled datasets, it is 487 *Trésor* T.1 pages, and no page of
it is scored. The pre-registered E5 gate, quoted verbatim in
`docs/pre-registration/2026-09-15-e5-alignment-gate.md`, together with the fact
that its source file is untracked and its only timestamp before this repository
was a filesystem mtime.

**Inputs.** `src/amadis_htr/fold.py`, `cer.py`, `resample.py`, `sampling.py`,
`data/gold/GUIDELINES.md`, `data/gold/splits/training-pages.csv`,
`docs/notes/2026-09-20-artefact-recovery.md`,
`docs/pre-registration/2026-09-15-e5-alignment-gate.md`.

**Status.** Writable now, except the gold-set paragraph's final counts.

**Not here.** Results. Protocol justifications belong here even when they are
uncomfortable, and the discomfort is not softened in section 8 instead.

## 6. Results

**Purpose.** State what was measured. Nothing else.

**Content.** One subsection per experiment, each opening with its claim, its unit of
analysis, its baseline and its uncertainty method, then the table, then the figure,
then one sentence naming the largest effect. No explanation, no comparison to the
literature, no speculation about cause.

| id | claim under test | unit | baseline | uncertainty | decision rule fixed in advance |
|---|---|---|---|---|---|
| E1 | the fine-tune reads both works better than the published models do | page | all of `stock`, `mccatmus` and `transkribus` are run, `transkribus` reported as confounded. Which one the headline is stated against is decided on the scores and recorded when decided | bootstrap over pages, 10,000 resamples, 95% | a difference smaller than the annotator's self-agreement CER is not claimed. One CER per work, and the 48 *Trésor* pages stay labelled validation |
| E2 | the accept rule keeps a generative pass from rewriting the text | suspect span | correction off, same recognition output | bootstrap over pages for the CER delta | the rejection rate is descriptive and the threshold sweep is exploratory, so no cell passes or fails |
| E3 | the LLM resolves ambiguous head and foot lines better than geometry alone | candidate line | always-`body`, and geometry without the LLM | bootstrap over pages | below 30 instances in a cell, the analysis degrades to a descriptive breakdown and says so |
| E4 | escalation and the lexicon earn their cost | drop cap | gate only, and no lexicon | bootstrap over pages | same 30-instance rule |
| E5 | a Trésor extract can be located in the baseline text | passage | none published, so the pre-registered gate stands in | bootstrap over passages | above 90% Livre accuracy proceeds, below roughly 80% stops the work, quoted verbatim in the pre-registration file |
| E6 | descriptive only | book, page | none | none, these are counts | reported only where a log or stored artefact backs it |

E6 has material today: 24 `run.json` files covering 14,111 pages with zero failures at
1.441 s/page over 5.65 hours, and 24 `calibration.json` files carrying per-book
structural recall and precision against the printed table of contents. Every one of
those numbers still has to pass through a tested harness module and
`eval/results/*.csv` before it reaches the page.

**Inputs.** `eval/results/*.csv` by way of `report/generated/`. Figures from
`figures/*.py`. Nothing typed.

**Status.** Blocked. E1 needs the gold set and a CUDA box, E2 needs Ollama, E3 and E4
need the annotation pass, E5 needs `data/runs/matcher/alignments.csv` which needs
database access and a go-ahead, E6 needs the harness modules that read the recovered
JSON. The fallbacks are the named ones in the implementation plan's blocked table.

**Not here.** Interpretation of any kind.

## 7. Error analysis and discussion

**Purpose.** Say what the numbers mean, and what they mean against the literature.

**Content.** Opens with the comparison move: where the two measured CERs sit relative
to what section 2 reported, and what the difference between the works says about a
model trained on one of them. Then the confusion table, quantifying the long `ſ`/`f`, `u`/`n`,
`c`/`e` and `H`/`R` confusions the project asserted and never counted. Then the
stratified reading, whether the fine-tune generalises evenly across the two type
families given that its training data is almost all *Trésor* T.1. Then what the LLM
passes tried to do and were refused, with a qualitative sample of rejected replies,
since that is C2's substance. Then localisation's failure cases, chapter against Livre,
and what the difference says about span selection rather than search.

**Inputs.** `eval/results/*.csv`, the rejected-reply sample committed under
`data/runs/`, section 2's bibliography.

**Status.** Blocked on section 6.

**Not here.** Any finding not already stated in section 6.

## 8. Limitations

**Purpose.** Bound every claim before a jury does.

**Content.** The gold set is 20 pages and one annotator, with self-agreement as the
noise floor. `val48` drove checkpoint selection, so it is validation and never test,
and page-level splitting of one volume leaves the same formes and type wear on both
The *Trésor* excerpts *Amadis de Gaule*, so on the *Amadis* pages the model has read
some of the text it is scored on even though it never saw those pages. The report
states that and does not correct for it. Transkribus segmented independently and cannot be brought under
the held-constant segmentation, so it stays a confounded baseline. E3 and E4 cells may
fall below 30 instances. The n8n production timings are on a machine not in scope, so
E6 covers the batch runner only. The Transkribus baseline output was searched for and
not found, so E1's fourth system may be absent.

**Inputs.** The design spec's risk table, the recovery note, section 6's realised cell
counts.

**Status.** Writable now in outline, final counts blocked.

**Not here.** Apology. Each limitation states its consequence for a specific claim.

## 9. Conclusion and released artefacts

**Purpose.** Close, and hand over something usable.

**Content.** What each of the three claims ended up supporting, in the numbers of
section 6. What the evaluation changed about the system, meaning which thresholds are
now calibrated rather than inherited. The artefacts: this repository, the frozen run
outputs, the gold set and its guidelines, the Hugging Face model card for
`amadis-ft.mlmodel`, now writable because the shipped file is tied to
`checkpoint_55-0.9950.ckpt` by weight comparison. What a successor should do first,
which is a second annotator and an inter-annotator figure.

**Inputs.** `report/generated/macros.tex`, `PROVENANCE.md`.

**Status.** Blocked on section 6, except the artefacts paragraph.

**Not here.** New results, new comparisons.

## References

`biblatex` with `biber`. To acquire, each with a verified DOI or a stable URL before it
is cited: the CATMuS dataset and model papers, CATMuS-Print [Large] at Zenodo record
10592716, the kraken engine, McCATMuS or whichever published early-modern model E1
adopts as its independent comparator, Transkribus as a platform, two to four papers on
LLM and neural post-correction of OCR, and one methodological reference for bootstrap
confidence intervals. Nothing is cited from memory.

## Appendices

- A. The annotation guidelines, verbatim from `data/gold/GUIDELINES.md`.
- B. The fold, as code.
- C. The three prompt versions of the coherence pass and the low-confidence prompt,
  verbatim, since E3 scores them against each other.
- D. Per-page results tables for E1, which do not belong in the body.
- E. The training split, its re-derivation and the per-collection accounting behind it.
- F. What the sanitiser removes from the vendored pipeline files and why.

## Page budget

| part | pages |
|---|---|
| abstract | 0.5 |
| 1. introduction | 2 |
| 2. related work | 2 |
| 3. corpus | 2.5 |
| 4. system | 4 |
| 5. protocol | 3 |
| 6. results | 7 |
| 7. error analysis and discussion | 2.5 |
| 8. limitations | 1 |
| 9. conclusion | 1 |
| body total | 25.5 |
| references | 1.5 |
| appendices | 6 |

Section 4 is the one at risk of expanding, because the engineering is the part with the
most sunk effort and the least evidentiary weight. Four pages is the cap, and the
threshold table is what earns them.

## The defence deck

`slides/main.tex` reads the same generated macros. It leads with the two findings a
jury will not expect, the *Amadis de Gaule* CER from E1 and the marker-anchor rejection
rate from E2, then the localisation sweep, then limitations. Sections 3 and 4 collapse
to one slide each. Nothing in the deck is a number that is not in the report.

## Sources consulted for the structure

- [GMU Writing Center, writing an IMRaD report](https://writingcenter.gmu.edu/writing-resources/imrad/writing-an-imrad-report):
  adopted the move structure for the introduction and the discussion, and the rule that
  results carry findings only and the discussion introduces none.
- [A practical playbook for statistical evaluation in ECE/CS papers](https://arxiv.org/html/2605.00428):
  adopted the per-experiment header of claim, unit of analysis, baseline and
  uncertainty, the preference for confidence intervals over standard errors, the
  instruction to compare against the strongest reasonable baseline rather than the
  easiest, and the requirement to state exclusion rules in advance. Its minimum of ten
  seeds does not transfer, because the unit of analysis here is an annotated page and
  there are twenty of them, which is why every figure carries a bootstrap interval.
- [University of the Sunshine Coast, IMRaD overview](https://libguides.usc.edu.au/scireport/imrad):
  adopted the broad-narrow-broad shape across the report as a whole.
