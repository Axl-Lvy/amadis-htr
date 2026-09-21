# E5 measured, 2026-09-21

The matcher ran against the amadis development database over the tailnet, read
only, through `scripts/alignment-export.ts` in the amadis working tree. Nothing
was written to any database. The raw export and the harness output are mirrored
at `~/amadis-artefacts/derived/matcher/` with their hashes in the mirror's
manifest.

## Two cohorts, never pooled

The database holds 459 passages in two import batches, and they are not the same
test set:

| batch | imported | what it is | pieces |
|---|---|---|---|
| workbook | 2026-09-14 | the reference workbook's rows, in its own order, starting at row 117 | 117 to 457 |
| catalogue | 2026-09-18 | the *Juxtalinéaire* catalogue's pieces, in narrative order | 1 to 116 |

The pre-registered gate was read on the workbook batch alone, when it was all
that existed. Scoring both together would be moving the test set after seeing
the numbers, so every figure below is per cohort.

## Rebuilding the piece key

`Passage.number` was removed from the schema, so nothing in the database says
which workbook row a passage is. `src/amadis_htr/piece_map.py` rebuilds it:

- **workbook batch, by position.** Sorted by import time, the *n*th passage is
  piece 117 + *n*. The title is the check, not the key: 339 of 341 titles agree
  with the workbook's at 0.85 or better. The two that do not are piece 144,
  whose database title is truncated mid-sentence, and piece 250, which differs
  by one missing space. Both are the same piece.
- **catalogue batch, by title.** 112 of 118 passages match a workbook piece at
  0.85 or better, each piece claimed once and best match first. Six passages
  stay unmapped rather than being guessed into a piece, and pieces 44, 66, 67
  and 68 end with no passage.

453 of 457 pieces therefore have a prediction.

## Result

Every passage was located: 459 of 459 carry a Livre, a start and an end.

| cohort | certain pieces | Livre correct | chapter correct | no printed number |
|---|---|---|---|---|
| workbook | 317 | 315 (99.4%) | 96 of 125 (76.8%) | 191 |
| catalogue | 101 | 100 (99.0%) | 38 of 52 (73.1%) | 49 |

The chapter denominator is the pieces where `decodeChapterLabel` recovers a
printed number from the label. Where it recovers none there is nothing to
compare, and `summarise()` sets those aside instead of failing them.

**Against the previously reported figures.** The project reported 100% Livre
(317 of 317) and 76.2% chapter (96 of 126) for this cohort. The chapter
numerator is identical and the denominator differs by one. The Livre figure is
99.4% rather than 100% because the earlier run scored against the claim stored
in the database, and a stored claim cannot be told apart from the matcher's own
past output, as the amadis harness says in its own comment. This run scores
against the editor's workbook, which is independent of both.

**The pre-registered gate passes.** It reads "correct LIVRE well above 90%
proceeds", and the workbook cohort is 99.4%.

**The three misses.** Pieces 223 and 224, both referenced to Livre 18, were
matched to Livre 8 at scores 0.924 and 0.942. Their stored claims say Livre 8
too, with chapters `XXII` and `XXVI` against the workbook's 22 and 26, so the
database agrees with the matcher and cannot arbitrate: that claim is derived
from the alignment. These two rows are what the 317 of 317 was made of. Either
the workbook's 18 is a slip for 8 or the matcher is wrong twice on adjacent
pieces, and only re-reading the *Trésor* settles it. Piece 47, referenced to
Livre 2, was matched to Livre 18 at 0.438, the lowest score in the export.

## What the sweep says about `MIN_SCORE = 0.808`

`eval/results/localisation-sweep-workbook.csv` and its catalogue counterpart
hold the curve from 0.40 to 1.00 in steps of 0.01.

On the workbook cohort precision sits at 0.994 from 0.40 to 0.85 while coverage
falls only from 1.000 to 0.981, so 0.808 buys nothing: it admits every piece the
cohort has, errors included. The constant is that cohort's own minimum score,
0.808219, rounded down to three decimals, which is what the project's note meant
by an empirically observed floor. It was read off this data rather than chosen
against a cost.

Buying out the two errors costs almost everything. They score 0.924 and 0.942,
so precision only reaches 1.000 at 0.95, and there coverage is 0.114, 36 pieces
of 317. At 0.93 precision is 0.991 for a coverage of 0.334. On this cohort the
matcher's score separates nothing useful, and the report says so rather than
recommending a threshold the curve does not support.

On the catalogue cohort the picture differs, because that batch has the one
low-scoring error. Precision reaches 1.000 at 0.80 and holds, for a coverage of
0.960. That is the case for a threshold, and it is the first evidence the
project has for one.

## Artefacts

| file | what it holds |
|---|---|
| `data/runs/matcher/alignments.csv` | 453 rows, `piece,cohort,passage_id,livre,chapter,start,end,score` |
| `data/runs/matcher/piece-map.csv` | how each piece was keyed, with the title agreement |
| `eval/results/localisation-summary-{workbook,catalogue}.csv` | the table above |
| `eval/results/localisation-sweep-{workbook,catalogue}.csv` | the threshold curve |

Titles are not committed. The map records the similarity, not the strings, so
the corpus stays where the data governance section puts it.
