# The E6 structural figures are hand-checked, 2026-09-22

`structure.csv` reports family A recalling 580 of its 587 printed chapters at a
precision of 77.4%. **Those are not the detector's unaided numbers**, and the
report may not present them as a measurement of the system.

## What the artefacts show

Every one of the 24 books carries a `corrections.json` beside its
`calibration.json`, holding two lists of line ids:

| | family A | all 24 books |
|---|---|---|
| `isChapter`, promoted to a chapter by hand | 128 | 217 |
| `notChapter`, demoted by hand | 217 | 441 |

The promotions are 17.1% of family A's 749 scored passages. The files say in
their own `_comment` what was done, in the first person of someone reading
pages:

> Hand-checked: three lines of OCR noise on the privilege leaf, and the table
> heading. | p.44 lines 36-40 promoted: chapter IIII; this title is set at body
> size — the tallest line is 143px against a 150px anchor threshold

> Hand-checked. Demoted: privilege/imprint, table heading and three table-leaf
> entries, prophecies and castle inscriptions, a descriptive figure note, ~20
> blocks of interpolated verse, three letters and a salutation, OCR noise, and
> the colophon.

`calibration.json` was written after `corrections.json` in 23 of the 24 books,
within the same minute. The scored passage set is therefore the corrected one.

## What this does to the figures

Bounds, not measurements, because the corrections cannot be undone from the
artefacts alone: the lists key on line ids and the scored passages are already
the post-correction set.

- **Precision.** 169 passages were still spurious after 217 had been demoted by
  hand. Had none been demoted and had all 217 been genuine false positives,
  precision would be 580 of 966, or 60.0%, against the 77.4% reported.
- **Recall.** 128 chapters were promoted by hand. Had none been and had all 128
  been missed by the detector, recall would be 452 of 587, or 77.0%, against the
  98.8% reported.

Both are worst cases. The true unaided figures lie between them and the
reported ones, and nothing in the frozen artefacts locates them.

## What was done about it

The two macros are renamed to carry the caveat onto the page:
`structRecallHandCheckedA` and `structPrecisionHandCheckedA`. A sentence citing
`\structRecallHandCheckedA` cannot describe it as the system's recall without
the name contradicting the prose.

## What would settle it

Re-running the detector over the same pages with `corrections.json` not applied,
and scoring that against the same printed tables of contents. The detector lived
in the home-lab OCR service, which is deleted; `notChapter` appears nowhere in
the surviving amadis working tree. Until it is recovered or rewritten, the
unaided structural figure does not exist and the report says so.
