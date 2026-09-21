# amadis-htr

Evaluation of a domain-adapted HTR pipeline for 16th-century French print,
built for the digitisation of *Amadis de Gaule* and the *Trésor des Amadis*.

This repository holds the evaluation, not the pipeline. The pipeline itself is
described in `pipeline/` as a sanitised snapshot, with its provenance recorded
in `PROVENANCE.md`.

## What reruns here

Everything under `src/amadis_htr/` runs on the frozen artefacts in `data/`,
with no GPU, no model server and no network:

```sh
uv run --extra dev pytest        # the harness's own tests
make all                         # the report and the defence deck
```

## What does not rerun here

Regenerating `data/runs/` means re-running recognition over the gold pages.
That needs the hardware described in the report: a machine with a CUDA GPU for
recognition and a local Ollama instance for the two LLM passes. The stored
outputs exist so that the evaluation is reproducible without it.

## Layout

| path | holds |
| --- | --- |
| `src/amadis_htr/` | the scoring code |
| `tests/` | one test module per source module |
| `data/gold/` | the annotated *Amadis de Gaule* gold set and its guidelines |
| `data/localisation/` | the human-assigned reference for passage localisation, and the map between the two piece catalogues |
| `eval/` | the scripts that derive a committed artefact from a source file held elsewhere |
| `data/runs/` | every system's frozen output, one file per system per page |
| `eval/results/` | the CSVs every figure and every reported number reads |
| `report/generated/` | LaTeX macros and tables written from those CSVs |
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
than reaching the page.

See `docs/specs/2026-09-18-amadis-htr-report-design.md` for the full design,
including the evaluation protocol, and `docs/plans/` for the implementation
plans.

## Licence

Code MIT (`LICENSE`). Data and figures CC-BY-4.0 (`LICENSE-DATA`).
