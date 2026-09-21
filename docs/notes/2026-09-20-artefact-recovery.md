# Artefact recovery, 2026-09-20

What spec section 10 listed as gaps, recovered from `bigpc` (tailnet host, user
`axel`). Every number below comes from a command run that day against the files
named here. Nothing was re-trained and no GPU ran.

## Where the artefacts actually live

The spec expected `amadis/ocr-training/artifacts/`. On bigpc that path is under
`~/IdeaProjects/amadis` (`~/amadis` is an empty directory), and two of the four
items were somewhere else entirely:

| item | bigpc path |
|---|---|
| training artefacts | `~/IdeaProjects/amadis/ocr-training/artifacts/` |
| the deployed model | `~/IdeaProjects/home-lab/services/ocr/models/amadis-ft.mlmodel` |
| run outputs | `~/Documents/Amadis de Gaule/ocr/book-{1..24}/` |
| Transkribus exports | `.../artifacts/source/export_job_28670809.zip` (PAGE XML), `_28670963.zip` (images) |

All of it is mirrored to `~/amadis-artefacts/` on the laptop. That mirror is
outside this repository and stays outside it: the page images and the PAGE XML
are the annotation campaign's output and their reuse terms are open question 1.

## G3: the training split, re-derived

`train.lst` and `val.lst` no longer exist anywhere. They are re-derivable,
because `ocr-training/prepare_data.py` splits deterministically:
`random.Random(seed).shuffle(...)` over a sorted, content-deduplicated page
list. The script has not changed since `b245a0c` (2026-07-07), the day the
deployed run trained.

Re-running it against both export zips with its default `--seed 13
--val-frac 0.1` reproduced the run's own counts, 439 train and 48 validation
pages out of 487 kept.

Counts alone do not identify the seed, so the split was checked against the
compiled datasets the run consumed. `train.arrow` and `val.arrow` carry line
text and line images and no page identifier, so the check compares line-text
multisets:

| split | pages | lines in the re-derived pages | lines in the arrow file | overlap |
|---|---|---|---|---|
| val | 48 | 1,397 | 1,397 | 1,397 (100%) |
| train | 439 | 12,600 | 12,600 | 12,600 (100%) |

Control, the same check with `--seed 42` over the same 487 pages: 176 of 1,397
val lines, 12.6%. The check discriminates, and seed 13 is the split that
trained.

Landed as `data/gold/splits/training-pages.csv`.

## G3, second half: no Livre page was ever in training

Every one of the 487 kept pages comes from Transkribus collection `10925942`,
*Trésor des Amadis* T.1. Full accounting of the two exports:

| collection | document | kept | no transcription | duplicate of a `10925942` page |
|---|---|---|---|---|
| 10925942 | Trésor des Amadis T.1 | 487 | 447 | |
| 10926025 | Trésor des Amadis T.2 | | 564 | |
| 15611103 | TRAINING_VALIDATION_SET_Amadis | | | 3 |
| 15648963 | TRAINING_VALIDATION_SET_Model_Name | | | 3 |
| 15708603 | TRAINING_VALIDATION_SET_Amadis_3 | | | 7 |
| 16685835 | TRAINING_VALIDATION_SET_Amadis_4 | | | 49 |

The 49 and the 7 are the counts the spec flagged as probably *Amadis de Gaule*
pages in training. They are not: each is byte-identical, by MD5 over the image
file, to a page already taken from T.1. `prepare_data.py` drops them as
duplicates, so they reached neither `train.arrow` nor `val.arrow`.

The two records G3 called irreconcilable turn out to describe the same
export at two stages. The deleted home-lab README's "roughly 549 pages over five
collections" is the export before deduplication: 487 + 49 + 7 + 3 + 3 = 549. Its
13,997 lines for T.1 are the lines that survived: 12,600 in `train.arrow` plus
1,397 in `val.arrow` is 13,997 exactly. The amadis README's "487 pages, split
439 / 48" is the same corpus after dedup. Neither record was wrong and neither
was authoritative on its own.

`excluded_livres()` therefore returns the empty set, and the `ood` frame is
unconstrained at page level.

**One caveat the report must state.** The *Trésor* is an anthology of extracts
from *Amadis de Gaule*. Page-level contamination is zero, but the model has
read the text of whichever Livres T.1 excerpts, and
`data/localisation/ground-truth.csv` is the map of which those are. Whether
that changes the frame is a judgement call, not a measurement, and it is open.

**Decided 2026-09-21.** It does not. Both works are the target domain, the
in-domain and out-of-domain framing is dropped, and E1 reports one CER per work.
The frame is all 24 books minus the pages listed here. See the decision at the
head of section 6 of the design spec.

## The deployed checkpoint is the one the README names

`amadis-ft.mlmodel` carries no accuracy or metrics metadata, so the link to a
checkpoint was established by comparing weights. Against
`checkpoint_55-0.9950.ckpt`: 38 of 38 parameter tensors present under matching
names, 26 bit-identical, and the 12 that differ are the three LSTM layers' bias
pairs. Those differ only in how the bias is split between `bias_ih` and
`bias_hh`, which the LSTM only ever uses as a sum, and the sums agree to
1.2e-07, float32 rounding.

Against `checkpoint_60`, `_63`, `_64`, `_65` (all 0.9949) and run 1's best
`checkpoint_07-0.9914.ckpt`: zero tensors in common.

`amadis-ft.mlmodel` sha256
`5bbf6972360f9677216adc000d59ea43c11d44c71e01b2fe606c3132f83e42b5`, and it is
the file all 24 `run.json` name as `model`. The Hugging Face model card can now
be written.

## Run outputs: 24 books, complete

Every `book-N/` holds both files the spec asked for.

`run.json` records input zip, pages requested, run, skipped and failed,
passages found, working width, workers, threads, device and wall-clock seconds.
Over the 24: **14,111 pages run, 0 failed, 20,329.7 s (5.65 h), 1.441 s/page**,
every book at 16 workers on the GPU. This is a batch-runner record and is not
the 348-page n8n production run, whose timings are still only on the mini PC.

`calibration.json` records, per book, `structural` (role counts over header,
body, footer and title, anomalies, pages), `toc` (entries, repaired numbers,
sequence breaks, suspect and missing folios) and `match` (recall, precision,
matched, missing, spurious, folio mismatches, unscorable). Book 1, for
instance: recall 0.971, precision 0.81 over 35 TOC chapters.

No number from these files is quoted in the report until a tested harness
module reads them into `eval/results/`. That is the next plan's work, not this
day's.

## What is still missing

- **The n8n execution database**, on the mini PC. Not touched: the user pointed
  at bigpc only.
- **The Transkribus baseline output** for E1. The two exports hold ground truth
  and images, not the annotators' model output. A search of bigpc's home for
  `export_job*`, for anything named after Transkribus and for PAGE XML outside
  those two zips returned the zips and nothing else.
- **`data/runs/matcher/alignments.csv`**, which needs database access and an
  explicit go-ahead.
- **"~0.58% on a standalone test"**, stated in the artefacts README with no
  artefact behind it. Treated like the other prose-only figures: re-measured by
  this harness or dropped.

## Reproducing this

On bigpc, from `~/IdeaProjects/amadis/ocr-training`:

```sh
unzip -q artifacts/source/export_job_28670809.zip -d /tmp/amadis-recover/xml
unzip -q artifacts/source/export_job_28670963.zip -d /tmp/amadis-recover/img
~/ocr-finetune/train-venv/bin/python prepare_data.py \
  --xml-root /tmp/amadis-recover/xml --img-root /tmp/amadis-recover/img \
  --out /tmp/amadis-recover/prep --val-frac 0.1 --seed 13
```

The work directory was 2.6 GB, measured before deletion, and was deleted once
the mirror verified. It rebuilds from the two zips, whose sha256 are in
`PROVENANCE.md`.

## The mirror

`~/amadis-artefacts/` on the laptop, 4,654,392,295 bytes over 1,944 files for
the training artefacts alone, byte count and file count both equal to the
source. `MANIFEST.sha256` at its root hashes all 2,091 files, the mirrored ones
and the derived ones together.

Not mirrored: the scans. `~/Documents/Amadis de Gaule/` on bigpc holds the 24
source PDFs, one zip and five repaired PDFs for books 13, 14, 15, 21 and 22,
13 GB in all. The gold set will need pages out of them, so the sampling frame
can be drawn here but the images stay on bigpc until their reuse terms are
checked.
