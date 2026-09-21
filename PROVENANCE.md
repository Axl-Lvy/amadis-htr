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

## Derived from files that are not committed

| source file | held where | destination | derived by |
|---|---|---|---|
| `Pièces des thresors.xlsx` | the editor's own copy | `data/localisation/ground-truth.csv` | `src/amadis_htr/ground_truth.py` |
| `Pièces des thresors.xlsx` and `Juxtalinéaire pièces. Corrigé.docx` | as above, and a corrector's copy | `data/localisation/juxtalineaire-map.csv` | `eval/derive_juxtalineaire_map.py`, read 2026-09-18 |

Neither source file is in this repository. The workbook is the editor's catalogue
and the docx is a corrector's unpublished transcription, so what is committed is
the derivation and its numeric output, never the text. Both derivations are
reproducible by anyone holding the sources.

## Figures that are not reproduced here

Numbers stated in prose in the source repositories, with no code, log or
committed artefact behind them, are not cited by this report. They are listed
here so the omission is deliberate and visible:

- stock CATMuS-Print at "approximately 1.5 to 2% CER" on this material
- the Transkribus annotators' own model at "approximately 0.3% CER"
- two disagreeing worker-scaling tables (8 workers at 1.75 against 1.92 s/page)
- the fine-tune at "approximately 0.58% CER on a standalone test", stated in the
  artefacts README with no test set, no log and no code behind it
- a "759-page corpus" whose scope nothing records

Each is either re-measured by this harness or dropped.

## Artefacts recovered from bigpc, 2026-09-20

Recovered over the tailnet from the host `bigpc`. None of it is committed here:
it is mirrored to `~/amadis-artefacts/` on the laptop, whose `MANIFEST.sha256`
hashes all 2,091 files. The training artefacts are 4,654,392,295 bytes over
1,944 files, file count and byte count both equal to the source. What each
artefact settles is recorded in
`docs/notes/2026-09-20-artefact-recovery.md`.

The two source repositories on bigpc are behind the clones this table records
above: amadis at `e34eb4c` (2026-09-16) against `3d5439d`, home-lab at
`f655ce4` (2026-09-16) against `4672c91`. Every artefact below is gitignored in
its repository, so those commits date the code beside the artefacts, not the
artefacts themselves.

| source on bigpc | mtime | sha256 |
|---|---|---|
| `IdeaProjects/amadis/ocr-training/artifacts/source/export_job_28670809.zip` | 2026-07-06 23:26 | `ee16e96511ca67fae0db105159cfa9cfc9518b36524a821449dec6b696157de1` |
| `IdeaProjects/amadis/ocr-training/artifacts/source/export_job_28670963.zip` | 2026-07-06 23:56 | `623f191a9035e773e8c8bed7f5f80f11346e6845291d59633e1fa3d3a7aea131` |
| `.../artifacts/run1-constant-lr0.001/train.arrow` | 2026-07-07 00:09 | `1bf942097874d1b79c940f079c5480517c56c80317357b7253986f6181163938` |
| `.../artifacts/run1-constant-lr0.001/val.arrow` | 2026-07-07 00:09 | `c638f3e167dfbcd5e2d70a34175b65868fcc1e9fb0b86d3870520e5389a4bcec` |
| `.../artifacts/runs/rop0.5-lr3e-4-augment/model/checkpoint_55-0.9950.ckpt` | 2026-07-07 20:57 | `6bb990906d843928d4af1093956fe87d45785eb85b8d079f21cf62ef5f8adb20` |
| `.../artifacts/runs/rop0.5-lr3e-4-augment/tblogs/.../events.out.tfevents.1783448827.AXL.98710.0` | 2026-07-07 | `eff84772b4a950e958a3ef9b401d116f1f116d9ce7093cd16e927eea3d764318` |
| `IdeaProjects/home-lab/services/ocr/models/amadis-ft.mlmodel` | 2026-07-07 21:21 | `5bbf6972360f9677216adc000d59ea43c11d44c71e01b2fe606c3132f83e42b5` |
| `Documents/Amadis de Gaule/ocr/book-{1..24}/run.json`, `calibration.json` | 2026-09-14, 2026-09-15 | in `MANIFEST.sha256` |

The rest of `artifacts/` (run 1's eleven checkpoints, the base model, the
drop-cap crops and candidates, the training logs) is mirrored and hashed in the
same manifest.

## Derived here, not copied

`data/gold/splits/training-pages.csv` is derived, because `train.lst` and
`val.lst` no longer exist. It is the output of `ocr-training/prepare_data.py`
at amadis `b245a0c`, unchanged since 2026-07-07, run against the two export
zips above with `--val-frac 0.1 --seed 13`, its own defaults. The seed is
confirmed by a 100% line-text match against `train.arrow` and `val.arrow`
where a seed-42 control matches 12.6%. The two re-derived lists are mirrored
as `derived/prep/train.lst`
(`a83d17034a78fda28a8aea3e7c9d5ce95f31a6e785bf099d176ffb38f1079085`) and
`derived/prep/val.lst`
(`fdb736f4e1eddb172bf4de38fb5f6a58d7f7fc516cd5312fa78a14b0a5d0e4e5`).

## Quoted, not copied wholesale

| source | destination | mtime | sha256 of the source | tracked at source |
|---|---|---|---|---|
| amadis `docs/superpowers/plans/2026-09-15-tresor-amadis-alignment-phase-a.md` | `docs/pre-registration/2026-09-15-e5-alignment-gate.md` | 2026-09-15 17:57 | `e417abdb245e836e1373f20fb344708bb2ba442ff17a6ca90968fdfadb310d04` | no, `**/docs/superpowers/` is globally ignored |

Only E5's pass and fail criteria are quoted. The rest of that plan is
implementation detail for the private repository.

## The matcher run, 2026-09-21

`data/runs/matcher/alignments.csv` is derived, not copied. It is the output of
`scripts/alignment-export.ts`, written for this purpose in the amadis working
tree and left uncommitted there, run with `--env-file=.env.local` against the
development database over the tailnet. The script reads and never writes. The
matcher never sees the claim: the claim columns in the raw export are read
separately and are not what any figure scores against.

| artefact | sha256 |
|---|---|
| raw export, `~/amadis-artefacts/derived/matcher/alignments-raw.csv` | `7220965980ef7a4f6699a871474705036d4ac4fd738646c8e191ea0f1aaf2a74` |
| `npm run harness:alignment` output, same directory | `5b8ac576cc68aa1ac069cea99c1779cb91b888d80602bd890e59231eae218b05` |

The raw export carries passage titles and is mirrored rather than committed,
because section 5 of the design spec keeps the corpus out of this repository.
What is committed is keyed by piece and records the title agreement as a number.
