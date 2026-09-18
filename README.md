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
| `data/gold/` | the out-of-domain gold set and its annotation guidelines |
| `data/localisation/` | the human-assigned reference for passage localisation, and the map between the two piece catalogues |
| `eval/` | the scripts that derive a committed artefact from a source file held elsewhere |
| `data/runs/` | every system's frozen output, one file per system per page |
| `eval/results/` | the CSVs every figure and every reported number reads |
| `report/generated/` | LaTeX macros and tables written from those CSVs |
| `pipeline/` | the sanitised pipeline snapshot |

See `docs/specs/2026-09-18-amadis-htr-report-design.md` for the full design,
including the evaluation protocol, and `docs/plans/` for the implementation
plans.

## Licence

Code MIT (`LICENSE`). Data and figures CC-BY-4.0 (`LICENSE-DATA`).
