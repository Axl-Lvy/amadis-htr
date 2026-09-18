# Provenance

Every file in this repository that was copied from elsewhere is recorded here,
with its source repository, source commit, source path and the date it was
copied.

## Source repositories

| repository | commit | date read | what came from it |
|---|---|---|---|
| `home-lab` (private) | `4672c91` | 2026-09-18 | the OCR service, the n8n workflow, the batch runner, the prompts |
| `amadis` (private) | `3d5439d` | 2026-09-18 | the training scripts, the matcher, the result contract |

Both source repositories are private and remain so. What is reproduced here is
the subset the report describes, sanitised by `src/amadis_htr/sanitise.py`.

## Copied files

| source | destination | commit | sanitised |
|---|---|---|---|
| `n8n/workflows/Q9jEMd6zCv9stSvV.json` | `pipeline/n8n/amadis-ocr.json` | `4672c91` | yes, 488,639 bytes in and 62,442 out |

See `pipeline/SANITISATION.md` for what the sanitiser removes and why.

## Figures that are not reproduced here

Numbers stated in prose in the source repositories, with no code, log or
committed artefact behind them, are not cited by this report. They are listed
here so the omission is deliberate and visible:

- stock CATMuS-Print at "approximately 1.5 to 2% CER" on this material
- the Transkribus annotators' own model at "approximately 0.3% CER"
- two disagreeing worker-scaling tables (8 workers at 1.75 against 1.92 s/page)
- a "759-page corpus" whose scope nothing records

Each is either re-measured by this harness or dropped.
