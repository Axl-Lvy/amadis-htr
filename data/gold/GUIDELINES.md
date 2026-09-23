# The gold set

118 pages carrying a corrected transcription, selected by
`eval/build_gold_set.py` from three Transkribus exports: 114 pages of *Trésor
des Amadis* T. 1 that the recognition model never read, corrected 15–18
September 2026, and 4 pages of *Amadis de Gaule* livre 13, corrected 4 June
2026. `MANIFEST.csv` carries one row per candidate page, kept or refused, with
the reason.

Nothing in this repository is annotated. These pages were corrected in
Transkribus in the course of the edition, and this directory selects and
publishes them. No figure in the report is scored against them.

## What the set cannot support

Four properties, each of which limits what a later comparison may conclude from
it. They are properties of how the pages were produced, and saying so does not
repair any of them.

1. **The reference is post-edited, not blind.** Every page was corrected on top
   of a model's own output — `model_id` 581889 for the 114, 554557 for the 4,
   recorded per page in the manifest's `seeded_by` column. A recognition error
   that reads plausibly survives correction, so the reference is biased towards
   the system that produced the seed, which is the fine-tune.
2. **The frame is one work and one copy.** 114 pages of *Trésor* T. 1 and 4 of
   one *Amadis* extract, not the 24 books. Stratification on type family and on
   scan provenance is not possible over a single copy, so the strata collapse
   to one cell and no generalisation across the corpus is supported.
3. **The segmentation is Transkribus's.** The reference carries Transkribus's
   own line boxes, so any comparison against Transkribus inherits them.
4. **There is no noise floor.** No page was transcribed twice, and there is one
   corrector, so there is no figure below which a difference between two
   systems is too small to claim.

## The transcription convention

What the corrected pages hold, which is the Transkribus convention the
recognition model was trained to emit. It is normalised rather than
diplomatic: the set records what the model should have produced, not what the
compositor set.

- **j and v are modern.** `auoit` is transcribed `avoit`, `Iamais` is
  transcribed `Jamais`.
- **Long s is transcribed `s`.** The printed `ſ` carries no information the
  reader needs.
- **Abbreviations are resolved.** A tilde over a vowel standing for a nasal is
  written out (`cõme` becomes `comme`). The `&` sign is kept as `&`, because it
  is a character the model must produce rather than an abbreviation to expand.
- **Drop caps are spelled out.** An ornamental initial `A` beginning `A madis`
  is transcribed `Amadis`.
- **Accents follow the print.** Modern accents the compositor did not set are
  not added, and the ones he did set are not removed.
- **Spelling is never modernised.** `nostre`, `estoit`, `troysiesme` and
  `aultres` are transcribed as printed. This is the single most important rule:
  the corpus's orthography is the object of study.

## Line and layout

- One reference line per printed line. Lines the compositor broke are not
  joined.
- A word broken across a line end keeps its hyphen as printed, including the
  `¬` form.
- The PAGE XML carries `readingOrder` and the line text. It carries no line
  roles, no drop-cap labels and no structure tags, so the set supports a
  transcription comparison and nothing else.

## What is out of the frame

Front matter is excluded and the exclusion is recorded:
`splits/excluded-pages.csv` holds the T. 1 title page, the one page refused on
that ground.

`splits/training-pages.csv` lists the 487 pages the model read, all of them
*Trésor des Amadis* T. 1. A page in that list is refused however well it is
corrected, so no page here is one the model was trained on.
