# amadis-htr: design for a public evaluation repository and report

Date: 2026-09-18
Status: approved, ready for an implementation plan
Deliverable: a written report in English plus an oral defence, graded as a data science / machine learning project, backed by a public repository
Sources reconstructed from: `home-lab` at `4672c91`, `amadis` at `3d5439d`

## 1. Problem

Two 16th-century corpora were digitised with a self-hosted HTR pipeline: the 24 books
of *Amadis de Gaule* (the baseline text, 1770 chapters, roughly 20 MB of transcription)
and the *Trésor des Amadis* anthologies that extract passages from it. The pipeline
combines a domain-adapted recognition model, geometric layout analysis, two LLM
post-processing passes, and a retrieval step that locates each Trésor extract inside
the baseline.

The system works and is in production. What does not exist is a measurement of it. The
only recognition figure anywhere is a validation CER on a 10% page-level split of a
single volume. There is no out-of-domain evaluation, no word error rate, no measured
baseline, no evaluation of either LLM pass, and the structural quality figures the
pipeline itself computes are discarded on import.

This repository exists to produce those measurements and the report that presents them.

## 2. Claims

Three evaluated contributions. Everything else is system description.

**C1. A domain-adapted HTR model for 16th-century French print.**
CATMuS-Print [Large] (Zenodo record 10592716, `catmus-print-fondue-large.mlmodel`)
fine-tuned with kraken 7.0.2 on Transkribus-corrected ground truth. Two configurations
were run: constant LR 1e-3 with no augmentation reached 0.86% val CER, and LR 3e-4 with
`reduceonplateau` (factor 0.5) plus augmentation reached 0.50%, early stopping at epoch
55 with `--lag 10`. The shipped artefact is `amadis-ft.mlmodel`, 22,890,323 bytes.
The contribution is evaluated in domain and, for the first time, out of domain.

**C2. LLM post-processing under a conservative accept rule.**
Two passes over recognised text. The first resolves whether an ambiguous line at the top
or foot of a page is a running head, a catchword, or body, by asking whether removing it
lets the neighbouring lines read continuously. The second re-reads words carrying a
character confidence below 0.6, with the suspect spans wrapped in `⟦ ⟧` markers.
The interesting mechanism is the accept rule: the reply is split on the markers and
accepted only when every segment outside them is byte identical to the original, so an
attempt to modernise the spelling is discarded rather than silently accepted. The failure
mode being defended against is the one a generative model actually has on this material.

**C3. Passage localisation as a retrieval task.**
Locating a Trésor extract (1411 code points on average) inside 3,646,003 word tokens of
baseline text, using a period-aware normaliser, a rare-word seed index (`length >= 6`,
document frequency `<= 200`, 518,743 seeds over 76,548 words) and per-book anchor
chaining. Reported at 100% Livre accuracy (317/317) and 76.2% chapter accuracy (96/126)
under a pass/fail gate written before the numbers were known.

## 3. Non-goals

Described in the report as system context, never presented as an evaluated result:

- the geometric layout rules (roles, titles by italic slant or by oversize, illustration
  and library-stamp suppression, reading order by baseline bands)
- the printed table of contents used as per-volume structural ground truth
- the per-book tuning profiles
- the n8n orchestration, the resume seam, the callback contract, the SSRF hardening
- the fork of the pipeline into a CPU service for the Trésor and a 16-worker GPU batch
  runner for the Livres

These are interesting engineering and they explain the numbers. They are not claims,
and the report must not let them expand into a system manual. Any of them may be cited
in a methods section or an appendix.

Also out of scope: re-running the production corpus, changing the amadis application,
and any write to the production database.

## 4. Repository architecture

Name: `amadis-htr`. Public, under the `Axl-Lvy` account. The local history is built and
sanitised first, and the GitHub repository is created public and receives that history as
its first push. Nothing is ever flipped from private to public, because a flip publishes
whatever the history already contains.

```
amadis-htr/
  README.md                  what this is, what reruns, what does not
  PROVENANCE.md              source commits, what was copied, what was sanitised
  LICENSE                    MIT (code)
  LICENSE-DATA               CC-BY-4.0 (data/ and figures/)
  CITATION.cff

  data/
    gold/
      GUIDELINES.md          the annotation convention, written before annotating
      MANIFEST.csv           one row per gold page: id, livre, folio, family,
                             provenance, scan source, why it was sampled
      pages/<id>.png         the page image at the working width
      text/<id>.txt          reference transcription
      lines/<id>.json        per-line reference: text, role, dropcap, polygon
      splits/                sampling seed, stratum assignment, the reannotated subset
    val48/                   the in-domain Transkribus validation split, as used in training
    localisation/
      ground-truth.csv       xlsx column B, normalised, with the ambiguous rows flagged
      pieces.csv             passage id, text, source edition
    runs/
      <system>/<page>.json   frozen raw output, one file per system per page
      INDEX.csv              system, model, flags, host, date, commit, run id

  pipeline/
    n8n/                     sanitised workflow export
    prompts/                 coherence and correction prompts, every version, dated
    ocr_service/             sanitised copy of the modules the report describes
    source_ocr/              sanitised copy of the batch runner modules
    training/                prepare_data.py, train.py, the ketos invocation
    SANITISATION.md          what was stripped and by which script

  src/amadis_htr/
    fold.py                  the single declared normalisation fold, shared
    cer.py                   E1
    resample.py              bootstrap confidence intervals
    ground_truth.py          the reference workbook into a typed reference
    localisation.py          E5
    correction.py            E2
    coherence.py             E3
    dropcap.py               E4
    throughput.py            E6
    sanitise.py              strips secrets from vendored pipeline files
    sampling.py              seeded stratified gold-page sampler
    report_macros.py         eval/results into LaTeX macros and tables
  tests/                     one module per source module

  eval/
    run_all.sh
    results/*.csv            the only thing figures and prose may read

  figures/
    *.py                     one matplotlib script per figure, reads eval/results
    *.pdf                    generated, never hand-made

  report/
    main.tex                 the report
    generated/               macros and tables written from eval/results, never edited
    refs.bib
  slides/
    main.tex                 the defence deck, Beamer, same generated/ by symlink
  docs/specs/                this file and its successors
```

Two rules the layout enforces:

1. **No number in the report is typed by hand.** Every figure in the prose is a LaTeX
   macro from `report/generated/macros.tex`, and every table is an `\input` of a file in
   the same directory. Both are written from `eval/results/*.csv` by
   `src/amadis_htr/report_macros.py`. `report/generated/` is regenerated, never edited, and
   a stale macro is a build error rather than a wrong number, because an undefined control
   sequence stops the build.
2. **`data/runs/` is frozen.** Evaluation reruns from stored outputs on any machine
   with Python. Regenerating `data/runs/` needs the big PC and an Ollama instance, and
   the README says so instead of pretending otherwise.

## 5. Data governance

Samples only. The full corpus stays in amadis behind Cloudflare Access.

- **Page images.** Provenance differs per volume: book 1 is a 315-file ZIP of bitonal
  600 dpi TIFFs from BM Lyon, books 3 and 4 are greyscale Gallica PDFs, book 18 is a
  Biblioteca Valenciana copy. Reuse terms must be checked per holding institution before
  any image is committed. Until that check is done, `data/gold/pages/` stays empty and
  `MANIFEST.csv` carries a stable page reference plus a resolvable link. This is a
  blocking task in the plan, not an afterthought.
- **Transcriptions.** 16th-century text is public domain. The reference transcriptions
  are new editorial work, released CC-BY-4.0.
- **Model weights.** `amadis-ft.mlmodel` published on Hugging Face with a model card.
  The card states the base model, the training data and its provenance, the split, the
  measured CER in domain and out of domain, the transcription convention the model emits,
  and the intended use. The card cannot be written until the Monday recovery confirms
  which checkpoint the shipped file came from.
- **Training data.** The Transkribus PAGE XML is released as a dataset only if the
  annotators agree. Ask before assuming. If they do not, the report describes the corpus
  and releases the split file without the content.

## 6. Evaluation protocol

### 6.0 The fold

One normalisation fold, defined once in `eval/fold.py`, applied identically to every
hypothesis and every reference wherever a folded figure is reported: Unicode NFC, case
folding, `u`/`v` collapsed, `i`/`j` collapsed, long `ſ` to `s`, and nothing else.

This fold is narrower than the matcher's `foldWord` in `lib/matching/normalize.ts`, which
also drops `s` before a consonant, folds `ph` to `f` and `y` to `i`, collapses doubled
letters and applies l-vocalisation. That normaliser is an instrument of C3 and is
described there. Using it to score C1 would hide real recognition errors, so E1 does not
use it.

**Why the fold exists.** The fine-tune was trained to emit the annotators' normalised
convention: modern j/v, resolved abbreviations, drop caps spelled out. Stock
CATMuS-Print emits diplomatic text. Scoring both against normalised gold charges the
stock model for a convention it was never asked to follow, so a raw comparison
attributes convention learning to recognition improvement.

Every E1 figure is therefore reported twice, raw and folded. The difference is the
convention effect on the characters the fold covers. Abbreviation resolution and drop-cap
spelling survive the fold, and their residual contribution is reported separately by
counting, on the gold set, how many reference characters come from a resolved
abbreviation or a spelled-out initial. That count bounds what the fold cannot remove.

### 6.1 E1, recognition

**Systems.**

| id | model | notes |
|---|---|---|
| `stock` | `catmus-print-fondue-large.mlmodel` | the fine-tune's own base, downloaded fresh from Zenodo |
| `ft` | `amadis-ft.mlmodel` | the shipped model |
| `transkribus` | the raw model output preserved from the annotation campaign | external baseline, not built here |
| `mccatmus` | McCATMuS, or another published early-modern print model from the kraken zoo | an independent comparator that is not the fine-tune's own base |

kraken 7.0.2 ships `blla` for segmentation and no bundled recognition model, so there is
no "kraken default" to compare against. The independent comparator has to be a published
model chosen on purpose. McCATMuS is the natural pick, and the project's own notes record
a McCATMuS A/B that was considered and never run.

**Segmentation is held constant by construction, not by assumption.** Every gold page is
rasterised once at the 2200 px working width, segmented once with `blla`, and that single
line set is handed to `stock`, `ft` and `mccatmus`. This matters more than it looks: the
two production pipelines rasterise differently (pipeline A at a caller-supplied dpi,
pipeline B at a fixed 2200 px), and the training README's own risk note records that a
drop cap only reaches the recognition line if segmentation includes it. Comparing models
across different line sets would measure segmentation. Transkribus segmented
independently and cannot be brought into this scheme, so it is reported as a confounded
baseline rather than corrected for.

**Test sets.**

- `val48`: the 48-page in-domain split from training (90/10 by page, seed 13, over
  *Trésor des Amadis* T.1). Reported as **validation, not test**, because
  `val_accuracy` drove checkpoint selection and early stopping. Page-level splitting of
  one printed volume also leaves the same formes, type case and wear on both sides, which
  the report states.
- `ood`: the new gold set from *Amadis de Gaule* (section 7), drawn only from Livres that
  gate G3 confirms were absent from training. This is the headline test set. "Out of
  domain" here means pages and volumes the model never saw, not the *Amadis de Gaule*
  edition as a whole: the Transkribus export lists `TRAINING_VALIDATION_SET_Amadis_4`
  (49 pages, 1,410 lines) and `_Amadis_3` (7 pages, 208 lines) among its collections, so
  roughly 56 pages of Livre material may be in the training corpus. The report states
  this plainly rather than claiming a cleaner separation than exists.

**Metrics.** CER and WER, raw and folded, per page and aggregated. Aggregation is
character-weighted (total errors over total reference characters), and the per-page
distribution is shown alongside so a single catastrophic page cannot hide.
Confidence intervals by bootstrap over pages, 10,000 resamples, because 20 pages is a
small sample and a point estimate alone would overstate precision.

**Error analysis.** A confusion table over the most frequent substitutions, which is
where the long `ſ` / `f`, `u` / `n`, `c` / `e` and `H` / `R` confusions named in the
project's own notes get quantified instead of asserted.

**Stratified reporting.** Every E1 figure is broken down by type family: books 1 to 12
(large folio, bâtarde type, roman folio numbers) against books 13 to 24 (a later,
smaller edition in clean roman type with italic rubrics and arabic page numbers). The
bulk of the training data is *Trésor* T.1, so both families are largely unseen, and
whether the fine-tune generalises evenly across them is a genuine finding either way it
comes out.

### 6.2 E2, low-confidence correction

**The grid.** Pipeline B accepts `--model` and `--llm` as flags, so four cells come free
on any page set: `{stock, ft} × {correction off, correction on}`.

**Run the grid on both test sets.** `val48` is *Trésor* material, which is where the
model is in domain and where the correction pass actually ran in production, so the
suspect-span rate there is the operationally meaningful one. Running E2 only on `ood`
would measure the pass on material whose suspect-span rate nothing has ever observed.
Both sets get the four cells and the two-model ablation.

**The model ablation.** The two pipelines run identical prompts against different
backends: `qwen3:8b` at temperature 0.3, `num_ctx` 16384 on the mini PC iGPU, and
`gpt-oss:20b` at temperature 0.0 on the RTX 4080. Same prompt, same accept rule, two
models. Run both on the gold set.

**Metrics**, computed per suspect span against the gold transcription:

- span-level precision, recall and F1 of the correction pass: of the spans flagged
  suspect, how many were genuinely wrong, how many the model fixed, how many it broke,
  how many it left alone correctly
- net CER delta, correction on against correction off, on the same recognition output
- **marker-anchor rejection rate**: the share of replies discarded because a segment
  outside the markers changed. Nothing in the pipeline counts this today, and it is the
  direct measure of how often the model tried to modernise the text
- a qualitative sample of rejected replies, since what the model tried to do is the
  substance of C2

**Threshold sensitivity.** `LOWCONF_THRESHOLD` is 0.6, raised from 0.5 on 2026-07-08
with no recorded measurement. Sweep it from 0.4 to 0.9 on the gold set and report the
resulting curve of spans flagged against errors caught. This turns an undocumented
constant into a calibrated choice.

**Confidence calibration.** A reliability curve relating the recogniser's per-character
confidence to observed error rate on the gold set. This is what justifies (or does not)
using 0.6 as a trigger at all, and it also speaks to amadis's `UNCERTAIN = 0.85` review
threshold, which is currently justified only by prose.

### 6.3 E3, header and footer coherence

**Labels.** Role labels (`body` / `header` / `footer`, with `kind` where applicable) are
annotated on every gold page in the same pass as the transcription, so E3 costs no extra
page openings.

**Metrics.** Accuracy, precision and recall per role on the candidate lines the layout
pass marks ambiguous, plus the confusion matrix. Compared against two baselines: always
answer `body` (the pipeline's own unparseable default, and the majority class), and the
geometry-only decision without the LLM.

**The position guards.** `applyVerdict` overrides the model whenever a top candidate is
called a footer or a bottom candidate a header. Count how often the guard fired and who
was right each time. A guard that never fires is dead code, and a guard that fires often
and is usually right is a result.

**Both models.** As in E2, `qwen3:8b` against `gpt-oss:20b` on identical prompts.

**Prompt versions.** Three versions exist and are dated in git: the six-line original
(`b5f0ee5`, 2026-07-08), the restructured version with the decisive test and the explicit
default to body (`a4223a3`, same day), and the addition of the line about footers being
short (`643dbc3`). Run all three on the gold set. Prompt iteration that was done by feel
becomes a measured ablation at no annotation cost.

### 6.4 E4, drop caps

**Labels.** The correct initial letter and its bounding region, annotated on the gold
pages alongside everything else.

**Metrics.** Letter accuracy overall and broken down by resolution source
(`gate`, `siglip`, `agree`, `context`, `unavailable`), the `needsReview` rate, and the
accuracy of the `needsReview` flag itself, meaning how often a flagged resolution was in
fact wrong.

**The escalation ablation.** The gate is ViT-B-32 (`laion2b_s34b_b79k`, 605 MB) and
escalation is ViT-L-16-SigLIP-256 (`webli`, 2.6 GB), triggered when the gate's top
probability falls below 0.6. Measure gate-only accuracy against gate-plus-escalation, so
the 2.6 GB and the roughly 3.9 GiB peak memory it costs are justified by a number.

**The context lexicon.** Measure resolution with and without the corpus-derived lexicon
completion, since it is the cheapest component and may be doing most of the work.

**Sweep `OCR_DROPCAP_MIN_PROB`** from 0.4 to 0.9 and report accuracy against escalation
rate.

### 6.5 E5, passage localisation

**Ground truth.** `Pièces des thresors.xlsx` column B, human-assigned, read from the
file and normalised into `data/localisation/ground-truth.csv`. The 21 rows recorded as
ambiguous are flagged and excluded from scoring, not silently dropped.

**This does not touch `Alignment` rows.** Since PR #124 removed `AlignmentStatus`, a
row's existence is the only location state, so a human's independent pick and the
matcher's own past output are indistinguishable. Scoring against that table would be
circular. The scorer is written fresh in this repository and reads only the xlsx and the
passage text.

**Metrics.** Top-1 Livre accuracy, chapter accuracy, and coverage (the share of passages
the matcher locates at all). Chapter scoring needs the printed chapter number, which
`decodeChapterLabel` recovers strictly from 1079 of 1770 labels (61%), so the chapter
figure rests on a subset and the report says which subset and why. The 180 labels that
would decode if a systematic leading `A` were repaired stay excluded, because `AVI` is
either `XVI` or `VI` and guessing would plant wrong ground truth.

**The score threshold sweep.** The headline E5 result. Sweep the acceptance threshold
across the observed score range and plot precision against coverage. This converts
`MIN_SCORE = 0.808`, currently an empirically observed floor living in an untracked
scratch file, into a calibrated decision boundary with a stated false-positive rate. Two
other undocumented thresholds appear in those scratch files, `overlap >= 0.6` and 5-gram
shingle agreement, and both are reported as what they are: ad hoc criteria applied once
to real data.

**Parameter sensitivity.** `MIN_SEED_LENGTH = 6`, `MAX_SEED_DF = 200`,
`CHAIN_GAP_PENALTY`, `CHAIN_BAND` and `WINDOW_SLACK = 200` have no recorded sensitivity
analysis, and the design spec says outright they were never tuned for recall. Sweep each
on the labelled set and report accuracy and latency against index size. A code comment
claims the seed cuts were "tuned from harness output"; the spec contradicts it. The
report resolves this by measuring, and does not cite either claim.

**Cross-method corroboration.** The matcher's per-Livre `found - claimed` delta
distribution reproduced an earlier independent SQL probe almost exactly across Livres 8,
11, 12, 13 and 4, despite sharing no code. This is the strongest single existing quality
result in the project and it is reported as such, with the small disagreement on Livre 4
(`-1×30, -3×16` against `-1×29, -3×15`) shown rather than smoothed.

**The pre-registered gate.** amadis `docs/superpowers/plans/2026-09-15-tresor-amadis-alignment-phase-a.md`
states pass and fail criteria before the numbers were known: above 90% Livre accuracy
proceeds, below roughly 80% stops the work, and a chapter figure far below the Livre
figure points at the span rather than the search. Quote it verbatim in the methods
section. Pre-registration is rare in a project like this and it is what makes the
observed 100% meaningful rather than post hoc.

### 6.6 E6, throughput and structural quality

Descriptive, not a claim, and reported only where a log or a stored artefact backs it.

- per-page wall time by stage (segmentation, recognition, post-processing) on both hosts
- the worker scaling table, re-measured with a committed log. The existing table (4×2
  through 32×1, best 16×1 at 1.61 s/page) and a second dataset in a docstring disagree
  on the 8-worker figure (1.75 against 1.92 s/page), and both are prose with no log
  behind them. Re-measure or omit both.
- per-volume structural recall and precision against the printed table of contents, from
  the recovered `calibration.json` files. Book 2's known figures are recall 0.727 (16 of
  22 chapters) and precision 0.842 (16 of 19 passages), with the pipeline's own reading
  that three of the six misses are table-parse failures rather than pipeline misses, so
  true recall lies between 0.73 and 0.86. Report the range, not the point.
- energy and wall-clock cost of a full corpus run, if the recovered `run.json` files
  support it. Nothing currently records cost of any kind.

## 7. Gold set construction

**One annotation pass, four label types.** The expensive act is opening a page and
reading it. Each gold page is transcribed, role-labelled, drop-cap-labelled and
region-marked in the same sitting. This is what makes the wide scope affordable: E3 and
E4 ride on E1's annotation cost instead of each needing their own campaign.

**Sampling frame.** Pages from *Amadis de Gaule*, restricted to the Livres that gate G3
shows contributed no page to training.
Stratified over:

- type family: books 1 to 12 against books 13 to 24
- scan provenance: bitonal 600 dpi TIFF (BM Lyon) against greyscale Gallica PDF, and the
  stamped Biblioteca Valenciana copy as its own stratum
- page kind: ordinary body pages only. Front matter, tables of contents, privilege
  leaves and pages dominated by a woodcut are excluded by the frame and the exclusion is
  recorded, because those are layout problems rather than recognition problems.

Selection is by a committed random seed within each stratum, and `MANIFEST.csv` records
why each page is in the set. Target 20 pages, revisable upward once the first three are
timed. At 20 to 40 minutes per dense page, 20 pages is roughly 10 hours.

**Convention.** `data/gold/GUIDELINES.md` is written and committed **before** annotation
begins. It fixes: diplomatic or normalised (normalised, matching the Transkribus
convention the model was trained to emit, so the comparison is fair), abbreviation
handling, drop-cap handling, line-break and hyphenation handling, what counts as a line,
and how illegible characters are marked.

**Reliability.** Single annotator. The report says so. Three pages are re-annotated blind
after a delay of at least a week and self-agreement is reported as CER between the two
passes. That number bounds the gold set's own noise floor, and any system difference
smaller than it is not a real difference. Presenting a self-agreement figure honestly is
worth more than an inter-annotator figure that does not exist.

**Tooling.** Annotate in Transkribus, which is already set up and exports PAGE XML with
line coordinates. Export and convert into `data/gold/lines/*.json`.

## 8. Contamination gates

Blocking tasks in the plan. Each produces an output file, not an assertion.

**G1. Juxtalinéaire against the training set.** `Juxtalinéaire pièces. Corrigé.docx`
holds 460 line-diplomatic pieces transcribing *Trésor* material, and the training corpus
is *Trésor* T.1. Cross-check the docx pieces against the 439 training pages. Any overlap
makes the docx usable for C3 only, never as OCR gold.

The numbering offset is derived, not remembered. `src/amadis_htr/juxtalineaire.py`
aligns the two catalogues on their titles and emits
`data/localisation/juxtalineaire-map.csv`. **The offset that had been remembered, +3
from piece 120 onward, is wrong.** It is a staircase, and it was measured on
2026-09-18 over all 457 workbook pieces at a mean title containment of 0.986:

| workbook pieces | docx pieces | offset |
|---|---|---|
| 1 to 38 | 1 to 38 | 0 |
| 39 to 67 | 40 to 68 | +1 |
| 68 to 82 | 70 to 84 | +2 |
| 83 to 457 | 86 to 460 | +3 |

Docx pieces 39, 69 and 85 have no workbook counterpart. Two are continuations the
docx prints as pieces of their own and the workbook folds into their predecessor, and
one is a second prophecy of Urgande the workbook does not list at all. Workbook piece
68 is the one genuine one-to-two pairing, and its low similarity in the map is the
signal that it is a merge rather than a match.

**G2. Gold set against training.** Confirm every `ood` page is from a Livre and appears
in no training or validation list. Emit the check's output.

**G3. Which pages actually trained the shipped model.** Two records describe different
corpora and neither is authoritative. The deleted home-lab training README reports 15,791
lines across roughly 549 pages spanning five Transkribus collections: T.1 at 487 pages /
13,997 lines, `TRAINING_VALIDATION_SET_Amadis_4` at 49 pages / 1,410 lines, `_Amadis_3`
at 7 pages / 208 lines, and two small collections that deduplicate against the others by
image hash. The amadis `ocr-training/README.md` describes T.1 alone, roughly 487 pages
and 14k lines, split 439 train / 48 val.

The likeliest reading is that the two describe different things, the full export against
what was shipped after the trainer moved repositories. That is a guess, and the report
cannot rest on it.

**The gate is the recovered `train.lst` and `val.lst`, not either README.** Read the page
list, derive which Livres contributed pages, and exclude every such Livre from the `ood`
sampling frame. Emit the derived list as `data/gold/splits/training-pages.csv`. Until
that file exists, no page is annotated and no E1 figure is written, because the sampling
frame depends on it.

## 9. Provenance and sanitisation

**Citable and not citable.** Code and PR bodies are citable. Prose-only numbers are not,
and each is re-measured or dropped. The list: stock CATMuS at "≈1.5 to 2% CER", the
Transkribus annotators' model at "≈0.3% CER", both throughput tables, and the
"759-page corpus" whose scope nothing records. Several amadis design documents holding
figures the report wants are gitignored and exist only in a working copy, so anything
cited from them is copied into this repository with its source path and date recorded in
`PROVENANCE.md`.

**Sanitisation is scripted.** `pipeline/sanitise.py` runs over the vendored copies and
its diff is reproducible. What it strips:

- `staticData.global` in the n8n workflow JSON, roughly 480 KB carrying real transcription
  text from a production run, a job id, a run id and the production callback URL
- credential ids (`FMANBA54S8FhsGYe`, `ZeAKqmw6m1Y1RHst`), the webhook id, workflow ids
- internal hostnames, the Tailscale and LAN addresses, the ntfy topic URL, the Vercel
  bypass token variable
- the callback host allowlist contents

The security design itself (an allowlist exists, redirects are refused, private address
ranges are refused) is described in prose, because it is a methods point. The hosts are
not.

`PROVENANCE.md` records the two source commits, `4672c91` (home-lab) and `3d5439d`
(amadis), the date of copying, and every file's origin path.

## 10. Artefact recovery

To be done on the big PC. Everything below is currently a gap the report cannot close
without it.

**Training artefacts**, under `amadis/ocr-training/artifacts/` (gitignored, may still be
on disk):

- `runs/rop0.5-lr3e-4-augment/model/checkpoint_55-0.9950.ckpt`, the named deployed
  checkpoint
- TensorBoard event files, for epoch count, the val CER curve and the val word accuracy
  that `train.py` logs but nothing records
- confirmation that `amadis-ft.mlmodel` was exported from that checkpoint. The Hugging
  Face model card depends on this, and it is not verifiable from either repository.
- the `train.lst` / `val.lst` pair, which settles G3

**Run outputs**, under the `source-ocr` `out/` directories: every `calibration.json` and
`run.json`. These hold per-volume recall, precision, missing, spurious, folio mismatches
and empty pages, computed by the pipeline and discarded by amadis. They are the only
systematic structural quality record the project ever produced and they exist nowhere
else.

**n8n execution database** on the mini PC: real per-page timings and failure counts for
the 348-page production run. The only surviving trace in git is undated residue in the
workflow's static data.

**Transkribus**: the raw model output preserved from the annotation campaign, exported as
PAGE XML, for the `transkribus` baseline in E1.

If an item cannot be recovered, the corresponding figure is dropped from the report
rather than estimated. The plan carries a named fallback for each.

## 11. Toolchain

**The report is LaTeX.** `report/main.tex` produces the PDF and `slides/main.tex` is a
Beamer deck for the defence. Both read the same generated macros and tables, so one
evaluation re-run updates the report and the deck together.

**Engine: LuaLaTeX or XeLaTeX, never pdfLaTeX.** The report quotes 16th-century French
verbatim and reproduces the correction pass's own markup, so the source carries long `ſ`
(U+017F) and the `⟦ ⟧` markers (U+27E6, U+27E7). pdfLaTeX cannot set those without
per-character workarounds. The document loads `fontspec` with a Unicode font that has the
coverage, and the font choice is recorded in `report/main.tex` rather than left to a
default.

**No LaTeX distribution is installed on this machine.** Two ways forward, and the choice
is recorded here rather than assumed:

- **Tectonic** (recommended): one binary into `~/.local/bin`, no `sudo`, fetches the
  packages a document actually uses and caches them. It is XeTeX-derived, so `fontspec`
  and Beamer work. A first build needs the network.
- **TeX Live** via the distribution's package manager. More complete, but `apt install`
  needs `sudo`, which this environment cannot supply, so the user runs it.

**Figures are matplotlib, saved as PDF** by one script per figure under `figures/`, each
reading only `eval/results/*.csv`, and included with `\includegraphics`. No figure is
drawn by hand and none is a screenshot.

**The numbers pipeline.** `src/amadis_htr/report_macros.py` reads `eval/results/*.csv` and
writes `report/generated/macros.tex` (one `\newcommand` per reported figure, with the
rounding fixed in one place) and one `.tex` table per result set, using `booktabs`. The
report `\input`s them. A figure that has not been measured therefore has no macro, and
citing it fails the build instead of reaching the page.

**Bibliography:** `biblatex` with `biber`, `report/refs.bib`. The related-work section
cites CATMuS, kraken, Transkribus and the LLM post-correction literature, so a real
bibliography is needed rather than a hand-written list.

Python 3.12 or later, `uv` for the environment. The two pipelines run 3.12 and the
harness is developed on 3.13; nothing in the scoring code depends on the difference,
and no `.python-version` pins it, so the lockfile records what was actually used.
`matplotlib` for figures. `jiwer` for CER and WER,
version pinned in the lockfile. **Whitespace counts as a character**, and reference and
hypothesis are compared as single strings with line breaks normalised to one space.
Line-break and word-boundary errors are real errors on this material, and discarding
whitespace would hide exactly the failures the layout pass exists to prevent. The choice
is stated in the report, because CER is not comparable across papers that make it
differently.

Everything in `eval/` runs on stored artefacts with no GPU, no Ollama and no network.

## 12. Report structure

1. Introduction: the corpus, the philological question, why off-the-shelf OCR is not
   enough for 16th-century French print
2. Related work: CATMuS, kraken, Transkribus, LLM post-correction of OCR
3. The corpus: two editions, two type families, three scan provenances, the numbers
4. System: recognition, layout, the two LLM passes, localisation. Compressed. This is
   where the non-goals live, and they get pages proportional to their evidentiary weight,
   not to how much work they were.
5. Evaluation protocol: the gold set, the fold, the contamination gates, the metrics
6. Results: E1 through E5, each with its ablation
7. Error analysis: what the model still gets wrong and what that implies
8. Limitations
9. Conclusion and released artefacts

The defence deck is a subset of the same content, leading with the out-of-domain result
and the marker-anchor rejection rate, because those are the two findings a jury will not
have expected.

## 13. Risks and degradation rules

| Risk | Rule |
|---|---|
| The in-domain split drove checkpoint selection | Reported as validation, never as test. The `ood` set is the headline. |
| Single annotator | Self-agreement reported as the noise floor. Differences below it are not claimed. |
| Small `ood` sample | Bootstrap intervals on every figure. No claim rests on a point estimate. |
| The fine-tune's advantage is partly convention | Every E1 figure reported raw and folded, with the unfoldable residual counted. |
| E3 and E4 label counts too thin at 20 pages | If a cell falls below 30 instances, that analysis degrades from a measured accuracy to a descriptive breakdown, and the report says so. |
| Scan reuse terms unclear | Images stay out of the repo until checked. Everything else ships. |
| Recovery fails on Monday | Each dependent figure has a named fallback or is dropped. No figure is estimated. |
| Some Livre pages were in training | The `ood` frame excludes every Livre that `train.lst` touches, and the report states how many Livre pages the fine-tune saw. |

## 14. Open questions

1. Whether the Transkribus annotators consent to the ground truth being released as a
   dataset. Affects section 5 only, not the evaluation.
2. Whether the scan holders' reuse terms permit committing page images.
3. Whether the raw Transkribus model output survives in an exportable form. If not, E1
   loses that baseline and rests on `stock` and `mccatmus`.
4. Deadline. The sample size in section 7 and the wide scope in section 6 both assume
   roughly 15 to 20 hours of manual work is available. If it is not, E3 and E4 are the
   first to drop, in that order.
