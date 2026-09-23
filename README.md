# amadis-htr

Evaluation of a domain-adapted HTR pipeline for 16th-century French print,
built for the digitisation of *Amadis de Gaule* and the *Trésor des Amadis*.

This repository holds the evaluation, not the pipeline. The pipeline itself is
described in `pipeline/` as a sanitised snapshot, with its provenance recorded
in `PROVENANCE.md`.

## What is not here

The report measures two stages: the correction pass's accept rule and passage
localisation, with throughput and structure described beside them. **It reports
no recognition accuracy** — no character error rate for the fine-tune, and no
comparison against the models it replaced. `data/gold/` is released and nothing
in the report is scored against it; `data/gold/GUIDELINES.md` states what that
set could and could not support if it were.

## What reruns here

Everything under `src/amadis_htr/` runs on the frozen artefacts in `data/`,
with no GPU, no model server and no network:

```sh
uv run --extra dev pytest        # the harness's own tests
./eval/run_all.sh                # every result CSV, macro, table and figure
make all                         # the report, its French edition and the deck
```

`eval/run_all.sh` rewrites every generated file from the frozen inputs. On
unchanged inputs it rewrites them **identically**, so `git diff` after a run is
the check that nothing drifted, and the suite asserts the same thing file by
file.

## What does not rerun here

Regenerating `data/runs/` means re-running the pipeline itself. That needs the
hardware described in the report --- a CUDA GPU for recognition, a local Ollama
instance for the LLM passes --- and the private pipeline checkout. The scripts
that do it are here and are named for it:

| script | what it freezes | needs |
| --- | --- | --- |
| `eval/freeze_ocr_runs.py` | the 24 books' run and calibration records | the run outputs |
| `eval/freeze_correction_reach.py` | E2's suspect-span census and sampling frame | the run outputs, the pipeline |
| `eval/run_correction.py` | E2's verdicts | the above, plus a GPU and Ollama |
| `eval/check_correction_determinism.py` | whether concurrency changes a verdict | the same |

Their outputs are committed so that everything above reruns without any of it.

## Layout

| path | holds |
| --- | --- |
| `src/amadis_htr/` | the scoring code |
| `tests/` | one test module per source module |
| `data/gold/` | 118 corrected pages, their manifest and what they can and cannot support |
| `data/localisation/` | the human-assigned reference for passage localisation, and the map between the two piece catalogues |
| `eval/` | the scripts that derive a committed artefact from a source file held elsewhere |
| `data/runs/` | every system's frozen output: the OCR run records, the matcher export, and E2's frame and verdicts |
| `docs/pre-registration/` | decisions committed before the numbers that test them |
| `eval/results/` | the CSVs every figure and every reported number reads |
| `report/generated/` | LaTeX macros, tables and figures written from those CSVs |
| `figures/` | the matplotlib scripts that draw every figure in the report |
| `report/plates/` | the illustrative plates: a page of the source print, and the line crops the layout stage keys on |
| `report/sections/` | one file per section of the report, each carrying its own drafting status |
| `report/sections-fr/` | the French edition's sections, translated from `report/sections/`, which stays canonical |
| `report/`, `slides/` | the report and the defence deck, sharing one preamble |
| `pipeline/` | the sanitised pipeline snapshot |

## Building the report

`make all` needs [Tectonic](https://tectonic-typesetting.github.io/) on the
path and nothing else. It fetches the LaTeX packages the documents actually
use and caches them, so the first build needs the network and later ones do
not.

The engine is XeTeX through Tectonic, never pdfLaTeX. The report quotes
16th-century print verbatim and reproduces the correction pass's own markup,
so the source carries long `ſ` (U+017F) and the `⟦ ⟧` markers (U+27E6,
U+27E7). The font is Libertinus, chosen because it is the one candidate that
covers all three: DejaVu Serif and Noto Serif were probed and neither has
U+27E6 or U+27E7.

The bibliography backend is `bibtex` rather than `biber`, for an environmental
reason recorded in `report/main.tex`. Installing `biber` makes that one word
changeable and nothing else.

`report/generated/` **is committed**, so the report builds from a fresh clone
without re-running the evaluation, and every file in it carries a header
saying it is generated. It is written by `src/amadis_htr/report_macros.py` and
never edited by hand. A number the evaluation has not produced has no macro,
and citing it is an undefined control sequence, which stops the build rather
than reaching the page. The same breakage is caught in the fast test suite, so
a section citing an unmeasured figure fails without a LaTeX toolchain present.

The French edition (`make report-fr`, `report/main-fr.pdf`) reads
`report/generated/fr/`, which the same scripts write from the same CSVs with
French number typography and translated labels. The English report is
canonical: a change lands in `report/sections/` first and is carried to
`report/sections-fr/` after.

The design notes, specifications and working notes this repository used to
carry were removed on 2026-09-22: the report states its own protocol, and the
history holds the rest. What survives is `docs/pre-registration/`, because a
gate written before the numbers is evidence rather than commentary. Those two
files are dated records and are left exactly as they were written, so they
still name experiments this project did not go on to run.

## Licence

Code MIT (`LICENSE`). Data and figures CC-BY-4.0 (`LICENSE-DATA`).
