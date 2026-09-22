# Gold set annotation guidelines

## What changed on 2026-09-22

Everything below was written before annotation began, and it still governs the
transcription convention. It no longer describes how the set was obtained.

The set is not 20 pages drawn by `src/amadis_htr/sampling.py` and annotated from
scratch. It is the 118 pages already corrected in Transkribus that the
recognition model never read: 114 of *Trésor* T. 1 outside the training split,
corrected 15–18 September 2026, and 4 of *Amadis de Gaule* livre 13, corrected
4 June 2026. `eval/build_gold_set.py` selects them and
`data/gold/MANIFEST.csv` records every candidate page with the reason it is in
or out. 118 pages against 20, at no annotation cost, and ten hours of annotation
was the binding constraint on the report.

Five things were given up for that, and none of them is repaired by saying so:

1. **The reference is post-edited, not blind.** Every page was corrected on top
   of a model's own output — `model_id` 581889 for the 114, 554557 for the 4,
   recorded per page in the manifest's `seeded_by` column. A recognition error
   that reads plausibly survives correction, so the reference is biased towards
   the system that produced the seed, which is the fine-tune. That bias points
   the same way as the report's headline claim.
2. **The frame is one work and one copy.** 114 pages of *Trésor* T. 1 and 4 of
   one *Amadis* extract, not the 24 books. Stratification on type family and on
   scan provenance is not possible over a single copy, so the strata collapse to
   one cell and no generalisation across the corpus is supported.
3. **The segmentation is Transkribus's.** The reference carries Transkribus's
   own line boxes. Any comparison against Transkribus inherits that, and it is a
   stronger objection than the confounded-baseline note the report already makes.
4. **The labels are transcription only.** No line roles, no drop caps, no
   structure tags — the PAGE XML carries `readingOrder` and nothing else. The
   four-labels-per-page claim below does not hold for this set, and the
   structural evaluation has nothing to score against.
5. **There is no noise floor.** No page was annotated twice, so the rule below
   — that no system difference smaller than the floor is claimed — currently has
   no number in it.

Points 1 and 5 are cheap to repair together, and should be: transcribe three of
the kept pages from scratch, blind, under the convention below, and diff against
the committed version. That is roughly an hour. It gives the floor point 5 needs
and it measures point 1 directly, turning the post-editing bias from a caveat
into a figure.

## The convention

Written before annotation begins. A convention settled halfway through is a
convention that differs across the set.

One annotator. Three pages are re-annotated blind after at least a week, and the
character error rate between the two passes is reported as the gold set's own
noise floor. No system difference smaller than that floor is claimed.

## What is annotated, in one pass per page

The expensive act is opening a page and reading it, so each page yields four
kinds of label at once:

1. the transcription, line by line
2. the role of each line: `body`, `header`, `footer`, `title`
3. the drop cap, if any: its letter and whether it is legible
4. the page's own structure: which lines belong to a chapter heading

## Transcription convention

**Normalised, matching the Transkribus convention the recognition model was
trained to emit.** A diplomatic convention would make the comparison unfair in
the opposite direction from a raw comparison, and the point of the gold set is
to score recognition, not to publish an edition.

- **j and v are modern.** `auoit` is transcribed `avoit`, `Iamais` is
  transcribed `Jamais`.
- **Long s is transcribed `s`.** The printed `ſ` carries no information the
  reader needs.
- **Abbreviations are resolved.** A tilde over a vowel standing for a nasal is
  written out (`cõme` becomes `comme`). The `&` sign is kept as `&`, because it
  is a character the model must produce rather than an abbreviation to expand.
- **Drop caps are spelled out.** An ornamental initial `A` beginning `A madis`
  is transcribed `Amadis`.
- **Accents follow the print.** Do not add modern accents the compositor did not
  set, and do not remove the ones he did.
- **Spelling is never modernised.** `nostre`, `estoit`, `troysiesme` and
  `aultres` are transcribed as printed. This is the single most important rule:
  the corpus's orthography is the object of study.

## Line and layout convention

- One reference line per printed line. Do not join lines that the compositor
  broke.
- A word broken across a line end keeps its hyphen as printed, including the `¬`
  form. Do not weld the halves.
- Running heads, catchwords, signatures and folio numbers are transcribed and
  labelled with their role, not omitted. The role labels are what the coherence
  evaluation scores.
- Illegible characters are marked `�`, one per illegible character. A line that
  is more than half illegible is excluded from the gold set and the exclusion is
  recorded in `MANIFEST.csv`.

## What is excluded from the frame

Front matter, privilege leaves, tables of contents, and pages more than half
occupied by a woodcut. Those are layout problems rather than recognition
problems, and the report says so rather than letting them depress a recognition
figure.

## Before any page is opened

`data/gold/splits/training-pages.csv` lists the 487 pages the model read, all of
them *Trésor des Amadis* T.1. The sampler subtracts them from the frame, so that
no page is annotated and scored that the model was trained on. The frame is
otherwise all 24 books: both works are the target domain, and nothing here is
sampled to prove a generalisation claim.
