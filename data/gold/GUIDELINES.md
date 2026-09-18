# Gold set annotation guidelines

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

`data/gold/splits/training-pages.csv` must exist, derived from the recovered
`train.lst`. The sampler refuses to run without it, because the Transkribus
export lists collections of *Amadis de Gaule* material alongside the *Trésor*,
so some Livres may already be in the training corpus and a contaminated frame
would be invisible.
