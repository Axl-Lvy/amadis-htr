# amadis-htr Evaluation Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the public repository skeleton and every evaluation instrument that can be written and tested without the artefacts still sitting on the big PC, so that Monday's recovery lands in a harness that already works.

**Architecture:** A `src/amadis_htr/` Python package holding pure, testable functions (the normalisation fold, CER and WER scoring, bootstrap intervals, ground-truth extraction, localisation scoring, pipeline sanitisation, gold-set sampling). Everything reads frozen artefacts from `data/` and writes CSV to `eval/results/`. Nothing in this plan touches a database, a GPU, an LLM or the network. The localisation ground truth is the one real dataset available today, and it is extracted for real.

**Tech Stack:** Python 3.12, `uv`, `pytest`, `jiwer` (CER and WER), `openpyxl` (the xlsx), `numpy` (bootstrap). Standard-library `csv` and `json` everywhere else.

**Spec:** `docs/specs/2026-09-18-amadis-htr-report-design.md`

## Global Constraints

- Repository: `/home/axel/IdeaProjects/amadis-htr`, currently a local git repo on branch `master` with two commits. Nothing has been pushed. Do not create a GitHub repository in this plan.
- The user's global gitignore at `/home/axel/.gitignore_global` excludes `**/docs/superpowers/`. This repository therefore uses `docs/specs/` and `docs/plans/`. Never create `docs/superpowers/` here.
- Python 3.12. `uv` is at `/home/axel/.local/bin/uv`. **No LaTeX distribution is installed** (no `pdflatex`, `xelatex`, `lualatex`, `latexmk`, `biber` or `tectonic`), and none is needed by this plan: the report is typeset in a later one. When it is, the engine must be LuaLaTeX or XeLaTeX, because the report quotes long `ſ` and the `⟦ ⟧` correction markers verbatim.
- No network access is required by any task. `uv` will download wheels on first sync, which is expected.
- **No number produced by this harness is ever typed into prose.** Every module writes CSV to `eval/results/`.
- The one declared fold (`amadis_htr.fold.fold`) is the only normalisation applied to a folded figure. The matcher's `foldWord` from amadis is a different thing and must never be imported or reimplemented here.
- Source corpus files live outside the repo and are never committed: `/home/axel/Downloads/Pièces des thresors.xlsx` and `/home/axel/Downloads/Juxtalinéaire pièces. Corrigé.docx`. Note the filename contains a non-ASCII character that some shells mangle, so always resolve it with a glob.
- Commit after every task. Commit messages use the Conventional Commits prefixes already used in this repo (`docs:`, `feat:`, `test:`, `chore:`).

---

## File Structure

| Path | Responsibility |
|---|---|
| `pyproject.toml` | package metadata, dependencies, pytest config |
| `.gitignore` | repo-local ignores (`.venv`, `__pycache__`, `eval/results/*.csv` is **not** ignored) |
| `src/amadis_htr/fold.py` | the one declared normalisation fold |
| `src/amadis_htr/cer.py` | CER and WER, per page and character-weighted aggregate |
| `src/amadis_htr/resample.py` | bootstrap confidence intervals over pages |
| `src/amadis_htr/ground_truth.py` | xlsx column B into a typed localisation reference |
| `src/amadis_htr/localisation.py` | E5 scoring and the score-threshold sweep |
| `src/amadis_htr/sanitise.py` | strips secrets and run residue from vendored pipeline files |
| `src/amadis_htr/sampling.py` | seeded stratified gold-page sampler |
| `eval/results/` | every CSV the report reads |
| `report/generated/` | LaTeX macros and tables written from those CSVs, committed, never edited |
| `tests/` | one test module per source module |
| `data/localisation/ground-truth.csv` | the real extracted reference, committed |
| `data/gold/GUIDELINES.md` | the annotation convention, written before annotating |

---

## Task 1: Repository bootstrap

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `README.md`, `PROVENANCE.md`, `LICENSE`, `LICENSE-DATA`, `src/amadis_htr/__init__.py`, `tests/test_smoke.py`
- Create (empty, with `.gitkeep`): `data/gold/pages/`, `data/gold/text/`, `data/gold/lines/`, `data/gold/splits/`, `data/localisation/`, `data/runs/`, `data/val48/`, `eval/results/`, `figures/`, `pipeline/`, `report/generated/`, `slides/`
- Modify: `docs/specs/2026-09-18-amadis-htr-report-design.md` (the repository tree in section 4)

**Interfaces:**
- Consumes: nothing.
- Produces: an importable `amadis_htr` package and a working `uv run pytest`. Every later task depends on both.

- [ ] **Step 1: Write the failing smoke test**

Create `tests/test_smoke.py`:

```python
def test_package_imports():
    import amadis_htr

    assert amadis_htr.__name__ == "amadis_htr"
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run pytest tests/test_smoke.py -v
```

Expected: FAIL. Either `uv` reports there is no project, or the collection fails with `ModuleNotFoundError: No module named 'amadis_htr'`.

- [ ] **Step 3: Create the package metadata**

Create `pyproject.toml`:

```toml
[project]
name = "amadis-htr"
version = "0.1.0"
description = "Evaluation harness for a domain-adapted HTR pipeline on 16th-century French print"
requires-python = ">=3.12"
dependencies = [
    "jiwer>=4.0",
    "numpy>=1.26",
    "matplotlib>=3.8",
    "openpyxl>=3.1",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/amadis_htr"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-q"
```

Create `src/amadis_htr/__init__.py`:

```python
"""Evaluation harness for the amadis HTR pipeline."""

__all__: list[str] = []
```

- [ ] **Step 4: Run the smoke test to verify it passes**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_smoke.py -v
```

Expected: PASS, 1 test.

- [ ] **Step 5: Create the ignore file**

Create `.gitignore`:

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
uv.lock.bak

# Page images are only committed once the holding institutions' reuse terms
# are checked. See the spec, section 5.
data/gold/pages/*
!data/gold/pages/.gitkeep

# Recovered artefacts land here and are vendored deliberately, never bulk-added.
data/runs/**/*.raw
```

Note: `eval/results/*.csv` is deliberately **not** ignored. Those files are the report's evidence and are committed.

- [ ] **Step 6: Create the directory skeleton**

```bash
cd /home/axel/IdeaProjects/amadis-htr
for d in data/gold/pages data/gold/text data/gold/lines data/gold/splits \
         data/localisation data/runs data/val48 eval/results figures \
         pipeline report/generated slides; do
  mkdir -p "$d" && touch "$d/.gitkeep"
done
```

`report/generated/` holds macros and tables written from `eval/results/*.csv`. It is
regenerated rather than edited, and it is committed, so the report builds from a clean
checkout.

- [ ] **Step 7: Write the licences**

Create `LICENSE` with the standard MIT licence text, copyright `2026 Axl-Lvy`.

Create `LICENSE-DATA`:

```text
The contents of data/ and figures/ are licensed under the Creative Commons
Attribution 4.0 International licence (CC-BY-4.0).

https://creativecommons.org/licenses/by/4.0/

The underlying 16th-century printed texts are in the public domain. The
transcriptions, annotations and derived tables in this directory are new
editorial work and are licensed as above.

Page images, where present, remain subject to the terms of the holding
institution recorded for each page in data/gold/MANIFEST.csv.
```

- [ ] **Step 8: Write the README**

Create `README.md`:

```markdown
# amadis-htr

Evaluation of a domain-adapted HTR pipeline for 16th-century French print,
built for the digitisation of *Amadis de Gaule* and the *Trésor des Amadis*.

This repository holds the evaluation, not the pipeline. The pipeline itself is
described in `pipeline/` as a sanitised snapshot, with its provenance recorded
in `PROVENANCE.md`.

## What reruns here

Everything in `eval/` runs on the frozen artefacts in `data/`, with no GPU, no
model server and no network:

```sh
uv run --extra dev pytest        # the harness's own tests
uv run python -m amadis_htr.cli  # regenerate eval/results/*.csv
```

## What does not rerun here

Regenerating `data/runs/` means re-running recognition over the gold pages.
That needs the hardware described in the report: a machine with a CUDA GPU for
recognition and a local Ollama instance for the two LLM passes. The stored
outputs exist so that the evaluation is reproducible without it.

## Layout

See `docs/specs/2026-09-18-amadis-htr-report-design.md` for the full design,
including the evaluation protocol and the annotation guidelines.

## Licence

Code MIT (`LICENSE`). Data and figures CC-BY-4.0 (`LICENSE-DATA`).
```

- [ ] **Step 9: Write the provenance skeleton**

Create `PROVENANCE.md`:

```markdown
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

Populated by the task that vendors the pipeline snapshot. Each row records the
source path, the destination path, the source commit and whether the file was
sanitised.

| source | destination | commit | sanitised |
|---|---|---|---|

## Figures that are not reproduced here

Numbers stated in prose in the source repositories, with no code, log or
committed artefact behind them, are not cited by this report. They are listed
here so the omission is deliberate and visible:

- stock CATMuS-Print at "approximately 1.5 to 2% CER" on this material
- the Transkribus annotators' own model at "approximately 0.3% CER"
- two disagreeing worker-scaling tables (8 workers at 1.75 against 1.92 s/page)
- a "759-page corpus" whose scope nothing records

Each is either re-measured by this harness or dropped.
```

- [ ] **Step 10: Align the spec's repository tree with the real layout**

The spec's section 4 tree puts the scoring code directly in `eval/`. A package
directory named `eval` sits awkwardly beside the `eval` builtin, so the code
lives in `src/amadis_htr/` and `eval/` holds only results and the driver.

In `docs/specs/2026-09-18-amadis-htr-report-design.md`, replace the `eval/`
block of the tree:

```
  eval/
    cer.py                   E1
    correction.py            E2
    coherence.py             E3
    dropcap.py               E4
    localisation.py          E5
    throughput.py            E6
    fold.py                  the single declared normalisation fold, shared
    bootstrap.py             confidence intervals
    run_all.sh
    results/*.csv            the only thing figures and prose may read
```

with:

```
  src/amadis_htr/
    fold.py                  the single declared normalisation fold, shared
    cer.py                   E1
    resample.py              bootstrap confidence intervals
    ground_truth.py          xlsx column B into a typed reference
    localisation.py          E5
    correction.py            E2
    coherence.py             E3
    dropcap.py               E4
    throughput.py            E6
    sanitise.py              strips secrets from vendored pipeline files
    sampling.py              seeded stratified gold-page sampler
  tests/                     one module per source module
  eval/
    run_all.sh
    results/*.csv            the only thing figures and prose may read
```

- [ ] **Step 11: Verify nothing in the tree is silently ignored**

The user's global gitignore excludes `**/docs/superpowers/`, and a repo-local
`.gitignore` cannot un-ignore a file inside an ignored directory, so the check
below matters. Run it **before** staging, because `git status --ignored` only
reports files that are still untracked.

```bash
cd /home/axel/IdeaProjects/amadis-htr
git status --porcelain --ignored | grep '^!!' || echo "nothing ignored"
git status --porcelain | grep '^??' | wc -l
```

Expected: the first command prints `nothing ignored`, or lists only `.venv/`,
`__pycache__/` and `data/gold/pages/*`, which are ignored on purpose. Any other
path appearing there is a file that would silently never be committed, and the
cause must be found before continuing. The second command reports the count of
files about to be added.

- [ ] **Step 12: Commit**

```bash
cd /home/axel/IdeaProjects/amadis-htr
git add -A
git commit -m "chore: bootstrap the evaluation repository

Package metadata, licences, README, provenance skeleton and the directory
layout. Code lives in src/amadis_htr/ rather than eval/, and the spec's tree
is updated to match."
```

---

## Task 2: The declared normalisation fold

**Files:**
- Create: `src/amadis_htr/fold.py`, `tests/test_fold.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `fold(text: str) -> str`. Task 3 uses it for every folded CER and WER figure. No other module may define a second fold.

Context an implementer needs: the fine-tuned model emits the annotators' normalised convention (modern j/v, resolved abbreviations, drop caps spelled out), while stock CATMuS-Print emits diplomatic text. This fold exists so both can be scored without charging the stock model for a convention it was never asked to follow. It is deliberately **narrower** than the matcher's `foldWord` in the amadis repository, which additionally drops `s` before a consonant, maps `ph` to `f` and `y` to `i`, collapses doubled letters and applies l-vocalisation. Those steps would hide real recognition errors, so they are absent here.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fold.py`:

```python
from amadis_htr.fold import fold


def test_long_s_becomes_s():
    assert fold("Eſtoit") == "estoit"


def test_case_is_folded():
    assert fold("MAISTRE") == fold("maistre")


def test_u_and_v_collapse_to_v():
    assert fold("auoit") == fold("avoit") == "avoit"


def test_i_and_j_collapse_to_i():
    assert fold("Jamais") == "iamais"


def test_the_fold_is_narrower_than_the_matchers():
    # The matcher folds these together. This fold must not, because the
    # difference between them is a real recognition difference.
    assert fold("nostre") != fold("notre")
    assert fold("elle") != fold("ele")
    assert fold("troysiesme") != fold("troisiesme")


def test_whitespace_is_preserved():
    assert fold("deux mots") == "devx mots"


def test_composed_and_decomposed_accents_agree():
    assert fold("était") == fold("était")


def test_fold_is_idempotent():
    once = fold("Eſtoit Jamais AUOIT")
    assert fold(once) == once


def test_empty_string():
    assert fold("") == ""
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_fold.py -v
```

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'amadis_htr.fold'`.

- [ ] **Step 3: Write the implementation**

Create `src/amadis_htr/fold.py`:

```python
"""The single declared normalisation fold used by every folded figure.

Deliberately narrower than the matcher's `foldWord`: it removes only the
differences that are conventions of transcription rather than differences of
recognition. Anything it removed beyond that would hide real errors.
"""

import unicodedata

LONG_S = "ſ"


def fold(text: str) -> str:
    """Normalise text for a convention-insensitive comparison.

    NFC, long s to s, case folding, u and v collapsed to v, i and j collapsed
    to i. Whitespace is preserved, because line-break and word-boundary errors
    are real errors on this material.
    """
    out = unicodedata.normalize("NFC", text)
    out = out.replace(LONG_S, "s")
    out = out.casefold()
    out = out.replace("u", "v")
    return out.replace("j", "i")
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_fold.py -v
```

Expected: PASS, 9 tests.

- [ ] **Step 5: Commit**

```bash
cd /home/axel/IdeaProjects/amadis-htr
git add src/amadis_htr/fold.py tests/test_fold.py
git commit -m "feat: the declared normalisation fold

Long s, case, u/v and i/j only. Narrower than the matcher's foldWord on
purpose, so that a folded CER still counts real recognition errors."
```

---

## Task 3: CER and WER scoring

**Files:**
- Create: `src/amadis_htr/cer.py`, `tests/test_cer.py`

**Interfaces:**
- Consumes: `amadis_htr.fold.fold`.
- Produces:
  - `flatten(text: str) -> str`
  - `PageScore` dataclass with fields `page_id: str`, `cer: float`, `wer: float`, `ref_chars: int`, `ref_words: int`, `char_edits: int`, `word_edits: int`
  - `score_page(page_id: str, reference: str, hypothesis: str, *, folded: bool = False) -> PageScore`
  - `aggregate(scores: Sequence[PageScore]) -> tuple[float, float]` returning `(cer, wer)`, character-weighted and word-weighted
  - `substitution_counts(reference: str, hypothesis: str) -> Counter[tuple[str, str]]`

Task 4 resamples `PageScore` lists. Task 6 does not use this module.

Context: CER is not comparable across papers that define it differently. This implementation fixes the definition. Whitespace **counts** as a character, and runs of whitespace are collapsed to a single space before comparison, so a line break in the hypothesis where the reference has a space is not an error while a missing word boundary is. That choice is stated in the report.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cer.py`:

```python
import math

from amadis_htr.cer import (
    PageScore,
    aggregate,
    flatten,
    score_page,
    substitution_counts,
)


def test_flatten_collapses_whitespace_runs():
    assert flatten("a  b\n c\t\td ") == "a b c d"


def test_identical_text_scores_zero():
    s = score_page("p1", "le roy Lisuart", "le roy Lisuart")
    assert s.cer == 0.0
    assert s.wer == 0.0
    assert s.char_edits == 0


def test_one_substituted_character():
    s = score_page("p1", "abcd", "abxd")
    assert s.ref_chars == 4
    assert s.char_edits == 1
    assert math.isclose(s.cer, 0.25)


def test_whitespace_counts_as_a_character():
    # A lost word boundary is one deletion, not a free pass.
    s = score_page("p1", "deux mots", "deuxmots")
    assert s.char_edits == 1
    assert s.ref_chars == 9


def test_word_error_rate():
    s = score_page("p1", "le roy Lisuart livra", "le roi Lisuart livra")
    assert s.ref_words == 4
    assert s.word_edits == 1
    assert math.isclose(s.wer, 0.25)


def test_folded_scoring_forgives_convention_only():
    raw = score_page("p1", "auoit", "avoit")
    folded = score_page("p1", "auoit", "avoit", folded=True)
    assert raw.char_edits == 1
    assert folded.char_edits == 0


def test_folded_scoring_still_counts_real_errors():
    folded = score_page("p1", "nostre", "notre", folded=True)
    assert folded.char_edits == 1


def test_aggregate_is_character_weighted_not_page_averaged():
    # A short perfect page must not offset a long bad one.
    long_bad = PageScore("a", 0.5, 0.5, 100, 20, 50, 10)
    short_good = PageScore("b", 0.0, 0.0, 10, 2, 0, 0)
    cer, wer = aggregate([long_bad, short_good])
    assert math.isclose(cer, 50 / 110)
    assert math.isclose(wer, 10 / 22)


def test_aggregate_of_nothing_is_zero():
    assert aggregate([]) == (0.0, 0.0)


def test_substitution_counts_reports_the_confused_pair():
    counts = substitution_counts("fecourir", "secourir")
    assert counts[("f", "s")] == 1


def test_empty_reference_and_hypothesis_score_zero():
    s = score_page("p1", "", "")
    assert (s.cer, s.wer, s.ref_chars, s.char_edits) == (0.0, 0.0, 0, 0)


def test_an_empty_reference_with_text_yields_no_rate():
    # Measured: jiwer counts 3 insertions and 0 hits, so ref_chars is 0 and no
    # rate is definable. Recorded here because excluded lines produce empty
    # reference segments and this must not raise or divide by zero.
    s = score_page("p1", "", "abc")
    assert s.ref_chars == 0
    assert s.cer == 0.0
    assert s.char_edits == 3


def test_an_empty_hypothesis_scores_a_total_loss():
    s = score_page("p1", "abc", "")
    assert s.ref_chars == 3
    assert s.char_edits == 3
    assert s.cer == 1.0
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_cer.py -v
```

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'amadis_htr.cer'`.

- [ ] **Step 3: Write the implementation**

Create `src/amadis_htr/cer.py`:

```python
"""Character and word error rates, with the definition pinned.

Whitespace counts as a character. Runs of whitespace collapse to one space
before comparison, so a line break where the reference has a space is not an
error while a lost word boundary is.
"""

import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

import jiwer

from amadis_htr.fold import fold

_WHITESPACE = re.compile(r"\s+")


def flatten(text: str) -> str:
    """Collapse whitespace runs to one space and strip the ends."""
    return _WHITESPACE.sub(" ", text).strip()


@dataclass(frozen=True)
class PageScore:
    page_id: str
    cer: float
    wer: float
    ref_chars: int
    ref_words: int
    char_edits: int
    word_edits: int


def score_page(
    page_id: str, reference: str, hypothesis: str, *, folded: bool = False
) -> PageScore:
    """Score one page. `folded` applies the declared fold to both sides."""
    ref, hyp = flatten(reference), flatten(hypothesis)
    if folded:
        ref, hyp = fold(ref), fold(hyp)

    chars = jiwer.process_characters(ref, hyp)
    words = jiwer.process_words(ref, hyp)

    char_edits = chars.substitutions + chars.deletions + chars.insertions
    ref_chars = chars.substitutions + chars.deletions + chars.hits
    word_edits = words.substitutions + words.deletions + words.insertions
    ref_words = words.substitutions + words.deletions + words.hits

    return PageScore(
        page_id=page_id,
        cer=char_edits / ref_chars if ref_chars else 0.0,
        wer=word_edits / ref_words if ref_words else 0.0,
        ref_chars=ref_chars,
        ref_words=ref_words,
        char_edits=char_edits,
        word_edits=word_edits,
    )


def aggregate(scores: Sequence[PageScore]) -> tuple[float, float]:
    """Character-weighted CER and word-weighted WER over pages.

    Weighted rather than averaged so that a short clean page cannot offset a
    long bad one.
    """
    ref_chars = sum(s.ref_chars for s in scores)
    ref_words = sum(s.ref_words for s in scores)
    char_edits = sum(s.char_edits for s in scores)
    word_edits = sum(s.word_edits for s in scores)
    return (
        char_edits / ref_chars if ref_chars else 0.0,
        word_edits / ref_words if ref_words else 0.0,
    )


def substitution_counts(reference: str, hypothesis: str) -> Counter:
    """Count substituted character pairs, for the error-analysis table."""
    ref, hyp = flatten(reference), flatten(hypothesis)
    out: Counter = Counter()
    result = jiwer.process_characters(ref, hyp)
    for chunks in result.alignments:
        for chunk in chunks:
            if chunk.type != "substitute":
                continue
            r = ref[chunk.ref_start_idx : chunk.ref_end_idx]
            h = hyp[chunk.hyp_start_idx : chunk.hyp_end_idx]
            for a, b in zip(r, h):
                out[(a, b)] += 1
    return out
```

- [ ] **Step 4: Run the tests**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_cer.py -v
```

Expected: PASS, 13 tests.

The API was verified against jiwer 4.0.0 before this plan was written:
`process_characters` and `process_words` return objects carrying
`substitutions`, `deletions`, `insertions`, `hits` and `alignments`, the
alignment chunk type for a substitution is `"substitute"`, and empty input does
not raise. If any of that has changed, check the installed version with
`uv run python -c "import importlib.metadata as m; print(m.version('jiwer'))"`
(the module has no `__version__` attribute) and raise the floor in
`pyproject.toml` rather than working around it. Do not hand-roll an edit
distance: the point of pinning a library is that the definition is citable.

- [ ] **Step 5: Commit**

```bash
cd /home/axel/IdeaProjects/amadis-htr
git add src/amadis_htr/cer.py tests/test_cer.py
git commit -m "feat: CER and WER with a pinned definition

Whitespace counts as a character, whitespace runs collapse to one space, and
the aggregate is character-weighted rather than page-averaged."
```

---

## Task 4: Bootstrap confidence intervals

**Files:**
- Create: `src/amadis_htr/resample.py`, `tests/test_resample.py`

**Interfaces:**
- Consumes: `amadis_htr.cer.PageScore`, `amadis_htr.cer.aggregate`.
- Produces: `bootstrap_cer(scores, *, resamples=10000, seed=0, alpha=0.05) -> tuple[float, float, float]` returning `(point, low, high)`.

Context: the out-of-domain gold set is about 20 pages. A point estimate alone would overstate precision, so every headline figure carries a percentile bootstrap interval resampled over **pages**, not over characters. Resampling characters would treat a page's errors as independent, which they are not: a badly segmented page fails as a page.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_resample.py`:

```python
import math

from amadis_htr.cer import PageScore
from amadis_htr.resample import bootstrap_cer


def _page(page_id: str, ref_chars: int, char_edits: int) -> PageScore:
    return PageScore(
        page_id=page_id,
        cer=char_edits / ref_chars,
        wer=0.0,
        ref_chars=ref_chars,
        ref_words=ref_chars // 5,
        char_edits=char_edits,
        word_edits=0,
    )


def test_point_estimate_matches_the_weighted_aggregate():
    pages = [_page("a", 100, 5), _page("b", 200, 5)]
    point, _, _ = bootstrap_cer(pages, resamples=200, seed=1)
    assert math.isclose(point, 10 / 300)


def test_interval_brackets_the_point_estimate():
    pages = [_page(str(i), 100, i) for i in range(20)]
    point, low, high = bootstrap_cer(pages, resamples=2000, seed=1)
    assert low <= point <= high


def test_identical_pages_give_a_degenerate_interval():
    pages = [_page(str(i), 100, 5) for i in range(10)]
    point, low, high = bootstrap_cer(pages, resamples=500, seed=1)
    assert math.isclose(low, point)
    assert math.isclose(high, point)


def test_seed_makes_it_reproducible():
    pages = [_page(str(i), 100, i) for i in range(20)]
    assert bootstrap_cer(pages, resamples=500, seed=7) == bootstrap_cer(
        pages, resamples=500, seed=7
    )


def test_different_seeds_differ():
    pages = [_page(str(i), 100, i) for i in range(20)]
    assert bootstrap_cer(pages, resamples=500, seed=7) != bootstrap_cer(
        pages, resamples=500, seed=8
    )


def test_empty_input_is_all_zero():
    assert bootstrap_cer([], resamples=10, seed=1) == (0.0, 0.0, 0.0)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_resample.py -v
```

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'amadis_htr.resample'`.

- [ ] **Step 3: Write the implementation**

Create `src/amadis_htr/resample.py`:

```python
"""Percentile bootstrap over pages.

Pages are the resampling unit, not characters: a page's errors are correlated,
because a badly segmented or badly inked page fails as a whole.
"""

from typing import Sequence

import numpy as np

from amadis_htr.cer import PageScore


def bootstrap_cer(
    scores: Sequence[PageScore],
    *,
    resamples: int = 10_000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Return (point estimate, lower bound, upper bound) for the CER."""
    if not scores:
        return (0.0, 0.0, 0.0)

    edits = np.array([s.char_edits for s in scores], dtype=float)
    chars = np.array([s.ref_chars for s in scores], dtype=float)
    point = float(edits.sum() / chars.sum()) if chars.sum() else 0.0

    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(scores), size=(resamples, len(scores)))
    totals = chars[draws].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        stats = np.where(totals > 0, edits[draws].sum(axis=1) / totals, 0.0)

    low, high = np.quantile(stats, [alpha / 2, 1 - alpha / 2])
    return (point, float(low), float(high))
```

- [ ] **Step 4: Run the tests**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_resample.py -v
```

Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
cd /home/axel/IdeaProjects/amadis-htr
git add src/amadis_htr/resample.py tests/test_resample.py
git commit -m "feat: percentile bootstrap over pages

Pages are the resampling unit because their errors are correlated. Every
headline CER carries an interval, since the gold set is about 20 pages."
```

---

## Task 5: Extract the localisation ground truth from the xlsx

**Files:**
- Create: `src/amadis_htr/ground_truth.py`, `tests/test_ground_truth.py`
- Create (generated, committed): `data/localisation/ground-truth.csv`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `Reference` dataclass with fields `piece: int`, `livre: int | None`, `chapter: int | None`, `confidence: str`, `raw: str`
  - `CONFIDENCES = ("certain", "conjecture", "uncertain", "none")`
  - `classify(raw: object) -> tuple[str, int | None, int | None]`
  - `read_workbook(path: str) -> list[Reference]`
  - `write_csv(references, path) -> None`

Task 6 reads the CSV this task writes.

Context: `Pièces des thresors.xlsx` is the human-assigned reference for where each Trésor piece sits in *Amadis de Gaule*. It has one sheet, `Feuil1`, 457 rows and no header row. Column A is `"<n>. <title>"`, column B is the location, column C the genre. Column B is not clean. Measured on the real file: 422 rows parse cleanly, 4 are wrapped in square brackets (an editor's conjecture), 10 carry a question mark (an editor's doubt), 14 are empty and 7 read `N/A`. Some rows name a Livre with no chapter (`Livre 2, ?`, `Livre 8`). The confidence column exists so the headline figure can rest on the certain rows while the rest are reported rather than silently dropped.

This is the **only** ground truth for E5. The `Alignment` table in amadis must never be used: since PR #124 removed `AlignmentStatus`, a human's pick and the matcher's own past output are indistinguishable there, so scoring against it would be circular.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ground_truth.py`:

```python
import glob

import pytest

from amadis_htr.ground_truth import Reference, classify, read_workbook, write_csv

XLSX = glob.glob("/home/axel/Downloads/*thresors.xlsx")


def test_clean_row_is_certain():
    assert classify("Livre 1, chap 9 ") == ("certain", 1, 9)


def test_trailing_period_is_still_certain():
    assert classify("Livre 5, chap 47.") == ("certain", 5, 47)


def test_bracketed_row_is_a_conjecture():
    assert classify("[Livre 2, chap 22]") == ("conjecture", 2, 22)


def test_bracketed_and_questioned_stays_a_conjecture():
    assert classify("[Livre 3, chap 3 ?]") == ("conjecture", 3, 3)


def test_question_mark_is_uncertain():
    assert classify("Livre 2, chap 6 (?)") == ("uncertain", 2, 6)


def test_unknown_chapter_keeps_the_livre():
    assert classify("Livre 2, ?") == ("uncertain", 2, None)
    assert classify("Livre 7, chap ??") == ("uncertain", 7, None)


def test_livre_alone_is_certain_with_no_chapter():
    assert classify("Livre 8") == ("certain", 8, None)


def test_empty_and_na_carry_no_reference():
    assert classify(None) == ("none", None, None)
    assert classify("   ") == ("none", None, None)
    assert classify("N/A") == ("none", None, None)


@pytest.mark.skipif(not XLSX, reason="the source workbook is not on this machine")
def test_the_real_workbook_parses_to_the_measured_counts():
    refs = read_workbook(XLSX[0])
    assert len(refs) == 457
    assert [r.piece for r in refs] == list(range(1, 458))

    tally = {c: sum(1 for r in refs if r.confidence == c) for c in
             ("certain", "conjecture", "uncertain", "none")}
    assert tally == {"certain": 422, "conjecture": 4, "uncertain": 10, "none": 21}

    scoreable = [r for r in refs if r.confidence == "certain" and r.chapter is not None]
    assert len(scoreable) == 421


def test_write_csv_round_trips(tmp_path):
    out = tmp_path / "gt.csv"
    write_csv([Reference(1, 4, 12, "certain", "Livre 4, chap 12")], out)
    text = out.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "piece,livre,chapter,confidence,raw"
    assert "1,4,12,certain,\"Livre 4, chap 12\"" in text
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_ground_truth.py -v
```

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'amadis_htr.ground_truth'`.

- [ ] **Step 3: Write the implementation**

Create `src/amadis_htr/ground_truth.py`:

```python
"""The human-assigned reference for where each Trésor piece sits in the baseline.

Read from `Pièces des thresors.xlsx` column B, which is prose written by an
editor rather than a clean field. Square brackets mark a conjecture and a
question mark marks doubt, so both survive into a confidence column instead of
being flattened away.

This is the only ground truth E5 may use. The `Alignment` table in amadis
cannot serve, because a human's pick and the matcher's own past output are
indistinguishable there.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import openpyxl

CONFIDENCES: tuple[str, ...] = ("certain", "conjecture", "uncertain", "none")

_LOCATION = re.compile(
    r"livre\s+([0-9]+)(?:\s*,\s*chap\.?\s*([0-9]+))?", re.IGNORECASE
)
_QUESTION = re.compile(r"\(?\?+\)?")
_PIECE = re.compile(r"^\s*([0-9]+)\s*\.")
_SHEET = "Feuil1"


@dataclass(frozen=True)
class Reference:
    piece: int
    livre: int | None
    chapter: int | None
    confidence: str
    raw: str


def classify(raw: object) -> tuple[str, int | None, int | None]:
    """Turn one column B cell into (confidence, livre, chapter)."""
    if raw is None:
        return ("none", None, None)

    text = str(raw).strip()
    if not text or text.upper() == "N/A":
        return ("none", None, None)

    confidence = "certain"
    if text.startswith("[") and text.endswith("]"):
        confidence = "conjecture"
        text = text[1:-1].strip()
    if "?" in text:
        # A bracketed conjecture that also carries a question mark stays a
        # conjecture: the editor's bracket is the stronger signal.
        if confidence != "conjecture":
            confidence = "uncertain"
        text = _QUESTION.sub("", text).strip()

    text = text.rstrip(". ").strip()
    match = _LOCATION.search(text)
    if match is None:
        return ("none", None, None)

    livre = int(match.group(1))
    chapter = int(match.group(2)) if match.group(2) else None
    return (confidence, livre, chapter)


def read_workbook(path: str | Path) -> list[Reference]:
    """Read every row of the reference workbook, in piece order."""
    sheet = openpyxl.load_workbook(path, data_only=True)[_SHEET]
    references: list[Reference] = []
    for row in range(1, sheet.max_row + 1):
        title = str(sheet.cell(row, 1).value or "")
        piece_match = _PIECE.match(title)
        if piece_match is None:
            # Trailing blank rows end the table. Anything else in column A is a
            # row the editor added in a shape this parser does not understand,
            # and silently skipping it would lose a reference.
            if not title.strip():
                break
            raise ValueError(f"row {row}: column A does not start with a number: {title!r}")
        cell = sheet.cell(row, 2).value
        confidence, livre, chapter = classify(cell)
        references.append(
            Reference(
                piece=int(piece_match.group(1)),
                livre=livre,
                chapter=chapter,
                confidence=confidence,
                raw="" if cell is None else str(cell).strip(),
            )
        )
    return references


def write_csv(references: Iterable[Reference], path: str | Path) -> None:
    """Write the reference table, one row per piece."""
    rows: Sequence[Reference] = list(references)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["piece", "livre", "chapter", "confidence", "raw"])
        for ref in rows:
            writer.writerow(
                [
                    ref.piece,
                    "" if ref.livre is None else ref.livre,
                    "" if ref.chapter is None else ref.chapter,
                    ref.confidence,
                    ref.raw,
                ]
            )
```

- [ ] **Step 4: Run the tests**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_ground_truth.py -v
```

Expected: PASS, 10 tests. The workbook test is skipped only if the file is absent.

- [ ] **Step 5: Generate the committed reference table**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run python - <<'PY'
import glob
from amadis_htr.ground_truth import read_workbook, write_csv

refs = read_workbook(glob.glob("/home/axel/Downloads/*thresors.xlsx")[0])
write_csv(refs, "data/localisation/ground-truth.csv")
print(len(refs), "references written")
PY
head -3 data/localisation/ground-truth.csv
wc -l data/localisation/ground-truth.csv
```

Expected: `457 references written`, and 458 lines in the file counting the header.

- [ ] **Step 6: Commit**

```bash
cd /home/axel/IdeaProjects/amadis-htr
git add src/amadis_htr/ground_truth.py tests/test_ground_truth.py data/localisation/ground-truth.csv
git commit -m "feat: extract the localisation ground truth from the reference workbook

457 pieces: 422 certain, 4 editorial conjectures, 10 uncertain, 21 with no
usable reference. The editor's brackets and question marks survive as a
confidence column rather than being flattened away."
```

---

## Task 6: Localisation scoring and the threshold sweep

**Files:**
- Create: `src/amadis_htr/localisation.py`, `tests/test_localisation.py`

**Interfaces:**
- Consumes: `data/localisation/ground-truth.csv` from Task 5.
- Produces:
  - `Prediction` dataclass with fields `piece: int`, `livre: int | None`, `chapter: int | None`, `score: float`
  - `read_ground_truth(path) -> dict[int, Reference]`
  - `read_predictions(path) -> dict[int, Prediction]`
  - `Summary` dataclass with fields `confidence: str`, `total: int`, `located: int`, `livre_correct: int`, `chapter_scoreable: int`, `chapter_correct: int`
  - `summarise(references, predictions) -> list[Summary]`
  - `sweep(references, predictions, thresholds) -> list[SweepRow]` where `SweepRow` has `threshold: float`, `accepted: int`, `correct: int`, `precision: float`, `coverage: float`
  - `write_summary(rows, path)` and `write_sweep(rows, path)`

Context: the matcher lives in the amadis repository, is written in TypeScript and needs the production database, so it cannot run here. Its output is vendored as a frozen artefact at `data/runs/matcher/alignments.csv` with the header `piece,livre,chapter,start,end,score`. Producing that file is a later task that needs database access and the user's go-ahead. This task builds the scorer and tests it against fixtures, so that the moment the artefact exists the figures follow.

The sweep is the headline E5 result. `MIN_SCORE = 0.808` currently lives in an untracked scratch file in the amadis repository, described there as the lowest score observed among already-curated passages. It is an observation, not a decision boundary. The sweep replaces it with a precision-against-coverage curve, from which a threshold can be chosen with a stated false-positive rate.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_localisation.py`:

```python
import math

from amadis_htr.ground_truth import Reference
from amadis_htr.localisation import (
    Prediction,
    read_ground_truth,
    read_predictions,
    summarise,
    sweep,
    write_sweep,
)


def _refs() -> dict[int, Reference]:
    return {
        1: Reference(1, 4, 12, "certain", "Livre 4, chap 12"),
        2: Reference(2, 4, 13, "certain", "Livre 4, chap 13"),
        3: Reference(3, 8, None, "certain", "Livre 8"),
        4: Reference(4, 2, 22, "conjecture", "[Livre 2, chap 22]"),
        5: Reference(5, None, None, "none", ""),
    }


def _preds() -> dict[int, Prediction]:
    return {
        1: Prediction(1, 4, 12, 0.95),   # right livre, right chapter
        2: Prediction(2, 4, 99, 0.90),   # right livre, wrong chapter
        3: Prediction(3, 9, 1, 0.70),    # wrong livre
        4: Prediction(4, 2, 22, 0.85),   # a conjecture, scored separately
        5: Prediction(5, 1, 1, 0.60),    # no reference, unscoreable
    }


def test_summary_is_broken_down_by_confidence():
    rows = {s.confidence: s for s in summarise(_refs(), _preds())}
    assert set(rows) == {"certain", "conjecture", "uncertain", "none"}


def test_certain_rows_score_livre_and_chapter_separately():
    certain = {s.confidence: s for s in summarise(_refs(), _preds())}["certain"]
    assert certain.total == 3
    assert certain.located == 3
    assert certain.livre_correct == 2          # pieces 1 and 2
    assert certain.chapter_scoreable == 2      # piece 3 has no reference chapter
    assert certain.chapter_correct == 1        # only piece 1


def test_rows_with_no_reference_are_counted_but_never_scored():
    none = {s.confidence: s for s in summarise(_refs(), _preds())}["none"]
    assert none.total == 1
    assert none.livre_correct == 0
    assert none.chapter_scoreable == 0


def test_a_missing_prediction_counts_as_not_located():
    preds = _preds()
    del preds[1]
    certain = {s.confidence: s for s in summarise(_refs(), preds)}["certain"]
    assert certain.total == 3
    assert certain.located == 2
    assert certain.livre_correct == 1


def test_a_prediction_with_no_livre_is_not_located():
    preds = _preds()
    preds[1] = Prediction(1, None, None, 0.0)
    certain = {s.confidence: s for s in summarise(_refs(), preds)}["certain"]
    assert certain.located == 2


def test_sweep_trades_precision_against_coverage():
    rows = {r.threshold: r for r in sweep(_refs(), _preds(), [0.0, 0.8, 0.92])}

    at_zero = rows[0.0]
    assert at_zero.accepted == 3           # the three certain pieces
    assert at_zero.correct == 2
    assert math.isclose(at_zero.precision, 2 / 3)
    assert math.isclose(at_zero.coverage, 1.0)

    at_high = rows[0.92]
    assert at_high.accepted == 1           # only piece 1 scores above 0.92
    assert at_high.correct == 1
    assert math.isclose(at_high.precision, 1.0)
    assert math.isclose(at_high.coverage, 1 / 3)


def test_sweep_precision_is_zero_when_nothing_is_accepted():
    row = sweep(_refs(), _preds(), [1.1])[0]
    assert row.accepted == 0
    assert row.precision == 0.0
    assert row.coverage == 0.0


def test_reading_the_real_ground_truth_file():
    refs = read_ground_truth("data/localisation/ground-truth.csv")
    assert len(refs) == 457
    assert refs[1].livre == 1
    assert refs[1].chapter == 9
    assert refs[1].confidence == "certain"


def test_reading_predictions(tmp_path):
    path = tmp_path / "alignments.csv"
    path.write_text(
        "piece,livre,chapter,start,end,score\n"
        "1,4,12,100,900,0.95\n"
        "2,,,,,0.0\n",
        encoding="utf-8",
    )
    preds = read_predictions(path)
    assert preds[1] == Prediction(1, 4, 12, 0.95)
    assert preds[2] == Prediction(2, None, None, 0.0)


def test_write_sweep_has_a_header(tmp_path):
    out = tmp_path / "sweep.csv"
    write_sweep(sweep(_refs(), _preds(), [0.0]), out)
    assert out.read_text(encoding="utf-8").splitlines()[0] == (
        "threshold,accepted,correct,precision,coverage"
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_localisation.py -v
```

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'amadis_htr.localisation'`.

- [ ] **Step 3: Write the implementation**

Create `src/amadis_htr/localisation.py`:

```python
"""E5: scoring the matcher against the editor's own reference.

The matcher runs in the amadis repository against the production database, so
its output arrives here as a frozen artefact, `data/runs/matcher/alignments.csv`
with the header `piece,livre,chapter,start,end,score`.

The sweep is the point of this module. A single accept threshold observed once
on curated data is not a decision boundary. A precision-against-coverage curve
is, and it lets the report state the false-positive rate that comes with any
threshold it recommends.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from amadis_htr.ground_truth import CONFIDENCES, Reference


@dataclass(frozen=True)
class Prediction:
    piece: int
    livre: int | None
    chapter: int | None
    score: float


@dataclass(frozen=True)
class Summary:
    confidence: str
    total: int
    located: int
    livre_correct: int
    chapter_scoreable: int
    chapter_correct: int


@dataclass(frozen=True)
class SweepRow:
    threshold: float
    accepted: int
    correct: int
    precision: float
    coverage: float


def _optional_int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def read_ground_truth(path: str | Path) -> dict[int, Reference]:
    """Read the table Task 5 wrote."""
    out: dict[int, Reference] = {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            piece = int(row["piece"])
            out[piece] = Reference(
                piece=piece,
                livre=_optional_int(row["livre"]),
                chapter=_optional_int(row["chapter"]),
                confidence=row["confidence"],
                raw=row["raw"],
            )
    return out


def read_predictions(path: str | Path) -> dict[int, Prediction]:
    """Read the frozen matcher output."""
    out: dict[int, Prediction] = {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            piece = int(row["piece"])
            out[piece] = Prediction(
                piece=piece,
                livre=_optional_int(row["livre"]),
                chapter=_optional_int(row["chapter"]),
                score=float(row["score"] or 0.0),
            )
    return out


def summarise(
    references: Mapping[int, Reference], predictions: Mapping[int, Prediction]
) -> list[Summary]:
    """One row per confidence band, so no piece is silently dropped."""
    rows: list[Summary] = []
    for confidence in CONFIDENCES:
        group = [r for r in references.values() if r.confidence == confidence]
        located = livre_correct = chapter_scoreable = chapter_correct = 0
        for ref in group:
            pred = predictions.get(ref.piece)
            if pred is None or pred.livre is None:
                continue
            located += 1
            if ref.livre is None:
                continue
            if pred.livre == ref.livre:
                livre_correct += 1
            if ref.chapter is None:
                continue
            chapter_scoreable += 1
            if pred.livre == ref.livre and pred.chapter == ref.chapter:
                chapter_correct += 1
        rows.append(
            Summary(
                confidence=confidence,
                total=len(group),
                located=located,
                livre_correct=livre_correct,
                chapter_scoreable=chapter_scoreable,
                chapter_correct=chapter_correct,
            )
        )
    return rows


def sweep(
    references: Mapping[int, Reference],
    predictions: Mapping[int, Prediction],
    thresholds: Sequence[float],
) -> list[SweepRow]:
    """Precision against coverage over accept thresholds, on the certain rows.

    Coverage is the share of scoreable pieces the threshold admits. Precision is
    the share of admitted pieces whose Livre is right.
    """
    scoreable = [
        r
        for r in references.values()
        if r.confidence == "certain" and r.livre is not None
    ]
    rows: list[SweepRow] = []
    for threshold in thresholds:
        accepted = correct = 0
        for ref in scoreable:
            pred = predictions.get(ref.piece)
            if pred is None or pred.livre is None or pred.score < threshold:
                continue
            accepted += 1
            if pred.livre == ref.livre:
                correct += 1
        rows.append(
            SweepRow(
                threshold=threshold,
                accepted=accepted,
                correct=correct,
                precision=correct / accepted if accepted else 0.0,
                coverage=accepted / len(scoreable) if scoreable else 0.0,
            )
        )
    return rows


def write_summary(rows: Iterable[Summary], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "confidence",
                "total",
                "located",
                "livre_correct",
                "chapter_scoreable",
                "chapter_correct",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.confidence,
                    row.total,
                    row.located,
                    row.livre_correct,
                    row.chapter_scoreable,
                    row.chapter_correct,
                ]
            )


def write_sweep(rows: Iterable[SweepRow], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["threshold", "accepted", "correct", "precision", "coverage"])
        for row in rows:
            writer.writerow(
                [
                    f"{row.threshold:.3f}",
                    row.accepted,
                    row.correct,
                    f"{row.precision:.6f}",
                    f"{row.coverage:.6f}",
                ]
            )
```

- [ ] **Step 4: Run the tests**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_localisation.py -v
```

Expected: PASS, 10 tests.

- [ ] **Step 5: Run the whole suite**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest -v
```

Expected: PASS, 49 tests across 6 files.

- [ ] **Step 6: Commit**

```bash
cd /home/axel/IdeaProjects/amadis-htr
git add src/amadis_htr/localisation.py tests/test_localisation.py
git commit -m "feat: localisation scoring and the accept-threshold sweep

Scores by confidence band so no piece is silently dropped, and replaces a
single observed accept score with a precision-against-coverage curve."
```

---

## Task 7: Sanitise and vendor the pipeline snapshot

**Files:**
- Create: `src/amadis_htr/sanitise.py`, `tests/test_sanitise.py`, `pipeline/SANITISATION.md`
- Modify: `PROVENANCE.md` (the copied-files table)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `sanitise_workflow(document: dict) -> dict` and `scrub_text(text: str) -> str`. Nothing later depends on them, but the vendoring step depends on both.

Context: the n8n workflow JSON in the home-lab repository is 488 KB, of which roughly 480 KB is `staticData.global`. That is residue from a real production run and it contains transcribed text from a 348-page job, the job id, the run id and the production callback URL. The file also carries credential ids, a webhook id and internal hostnames. None of it may reach a public repository. The security design is described in the report in prose, because it is a methods point. The hosts are not.

The scrubbing is a script rather than a manual pass so its diff is reproducible and a reviewer can check what was removed.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sanitise.py`:

```python
import json

from amadis_htr.sanitise import sanitise_workflow, scrub_text


def test_static_data_is_removed_entirely():
    doc = {"name": "amadis-ocr", "staticData": {"global": {"amadisPrev": "..."}}}
    assert "staticData" not in sanitise_workflow(doc)


def test_credential_ids_are_removed_but_the_name_is_kept():
    doc = {
        "nodes": [
            {
                "name": "Webhook",
                "credentials": {"httpHeaderAuth": {"id": "FMANBA54S8FhsGYe",
                                                   "name": "OCR Webhook"}},
            }
        ]
    }
    node = sanitise_workflow(doc)["nodes"][0]
    assert node["credentials"]["httpHeaderAuth"] == {"name": "OCR Webhook"}


def test_webhook_id_is_removed():
    doc = {"nodes": [{"name": "Webhook", "webhookId": "53437b11-ecc6-4451-97b0"}]}
    assert "webhookId" not in sanitise_workflow(doc)["nodes"][0]


def test_workflow_and_version_ids_are_removed():
    doc = {"id": "Q9jEMd6zCv9stSvV", "versionId": "81319df6", "name": "amadis-ocr"}
    out = sanitise_workflow(doc)
    assert "id" not in out and "versionId" not in out
    assert out["name"] == "amadis-ocr"


def test_error_workflow_id_is_removed_from_settings():
    doc = {"settings": {"executionOrder": "v1", "errorWorkflow": "fDYSwKxnDbeWDBka"}}
    settings = sanitise_workflow(doc)["settings"]
    assert settings == {"executionOrder": "v1"}


def test_hostnames_inside_node_parameters_are_scrubbed():
    doc = {
        "nodes": [
            {
                "name": "Validate",
                "parameters": {
                    "jsCode": 'const HOSTS = ["amadis.axl-lvy.fr", "amadis-preview.axl-lvy.fr"];'
                },
            }
        ]
    }
    code = sanitise_workflow(doc)["nodes"][0]["parameters"]["jsCode"]
    assert "axl-lvy.fr" not in code
    assert "example.invalid" in code


def test_scrub_replaces_every_private_host_form():
    text = (
        "https://amadis.axl-lvy.fr/api/ocr/callback\n"
        "https://ntfy.axl-lvy.fr/n8n-errors\n"
        "http://ollama:11434/api/chat/\n"
        "192.168.1.66 and 100.94.250.14 and 10.0.0.5\n"
    )
    out = scrub_text(text)
    assert "axl-lvy.fr" not in out
    assert "192.168.1.66" not in out
    assert "100.94.250.14" not in out
    assert "10.0.0.5" not in out
    # Every branch must eat all four octets. A three-octet match would leave a
    # stray ".5" behind and look like it had worked.
    assert "0.0.0.0 and 0.0.0.0 and 0.0.0.0" in out
    # Container names on a private docker network are not secrets and stay,
    # because the report describes the service graph.
    assert "http://ollama:11434/api/chat/" in out


def test_a_version_number_is_not_mistaken_for_an_address():
    assert scrub_text("kraken 10.5 and torch 2.10.0") == "kraken 10.5 and torch 2.10.0"


def test_scrubbing_is_idempotent():
    once = scrub_text("https://amadis.axl-lvy.fr/x")
    assert scrub_text(once) == once


def test_a_pinned_sample_round_trips_through_json():
    doc = {"name": "amadis-ocr", "staticData": {"global": {}}, "nodes": []}
    assert json.loads(json.dumps(sanitise_workflow(doc))) == {"name": "amadis-ocr",
                                                              "nodes": []}
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_sanitise.py -v
```

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'amadis_htr.sanitise'`.

- [ ] **Step 3: Write the implementation**

Create `src/amadis_htr/sanitise.py`:

```python
"""Strip secrets and production residue from vendored pipeline files.

Scripted rather than done by hand so that the diff is reproducible and a
reviewer can check what was removed. The security design of the original
pipeline is described in the report as a methods point. Its hosts, credential
ids and run residue are not.
"""

import copy
import re
from typing import Any

PLACEHOLDER_HOST = "example.invalid"
PLACEHOLDER_IP = "0.0.0.0"

# The private DNS zone used throughout the deployment, plus the two private
# address ranges that appear in the host documentation.
_PRIVATE_DOMAIN = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.axl-lvy\.fr\b", re.I)
# Each branch must consume all four octets. Writing the shared tail once, as
# `(?:192\.168|10|100\....)\.\d{1,3}\.\d{1,3}`, gives the 10/8 branch only
# three octets, so `10.0.0.5` matches `10.0.0` and leaves a stray `.5` behind.
_PRIVATE_IPV4 = re.compile(
    r"\b(?:"
    r"10(?:\.\d{1,3}){3}"
    r"|192\.168(?:\.\d{1,3}){2}"
    r"|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])(?:\.\d{1,3}){2}"
    r")\b"
)

_DROP_TOP_LEVEL = ("staticData", "pinData", "id", "versionId", "meta", "shared")
_DROP_SETTINGS = ("errorWorkflow", "callerPolicy")
_DROP_NODE = ("webhookId", "id")


def scrub_text(text: str) -> str:
    """Replace private hostnames and addresses with placeholders.

    Container names on the private docker network (`ocr`, `ollama`, `n8n`) are
    left alone: they are not secrets, and the report describes that service
    graph.
    """
    out = _PRIVATE_DOMAIN.sub(PLACEHOLDER_HOST, text)
    return _PRIVATE_IPV4.sub(PLACEHOLDER_IP, out)


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if isinstance(value, dict):
        return {key: _scrub(item) for key, item in value.items()}
    return value


def sanitise_workflow(document: dict) -> dict:
    """Return a copy of an n8n workflow export that is safe to publish."""
    out = copy.deepcopy(document)

    for key in _DROP_TOP_LEVEL:
        out.pop(key, None)

    settings = out.get("settings")
    if isinstance(settings, dict):
        for key in _DROP_SETTINGS:
            settings.pop(key, None)

    for node in out.get("nodes", []):
        if not isinstance(node, dict):
            continue
        for key in _DROP_NODE:
            node.pop(key, None)
        credentials = node.get("credentials")
        if isinstance(credentials, dict):
            for slot, detail in credentials.items():
                if isinstance(detail, dict):
                    credentials[slot] = {
                        k: v for k, v in detail.items() if k == "name"
                    }

    return _scrub(out)
```

- [ ] **Step 4: Run the tests**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_sanitise.py -v
```

Expected: PASS, 10 tests.

- [ ] **Step 5: Vendor the workflow**

```bash
cd /home/axel/IdeaProjects/amadis-htr
mkdir -p pipeline/n8n
uv run python - <<'PY'
import json
from pathlib import Path
from amadis_htr.sanitise import sanitise_workflow

src = Path("/home/axel/IdeaProjects/home-lab/n8n/workflows/Q9jEMd6zCv9stSvV.json")
raw = json.loads(src.read_text(encoding="utf-8"))
clean = sanitise_workflow(raw)
out = Path("pipeline/n8n/amadis-ocr.json")
out.write_text(json.dumps(clean, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"{src.stat().st_size} bytes in, {out.stat().st_size} bytes out")
PY
```

Expected: roughly 488,000 bytes in and well under 30,000 bytes out. If the
output is still in the hundreds of kilobytes, `staticData` was not removed and
the file must not be committed.

- [ ] **Step 6: Verify nothing sensitive survived**

```bash
cd /home/axel/IdeaProjects/amadis-htr
grep -c 'axl-lvy\.fr\|staticData\|amadisPrev\|webhookId\|FMANBA54S8FhsGYe\|ZeAKqmw6m1Y1RHst\|Q9jEMd6zCv9stSvV\|fDYSwKxnDbeWDBka' pipeline/n8n/amadis-ocr.json
```

Expected: `0`. `grep -c` exits 1 when it finds nothing, which is the pass
condition here. If any count is above zero, stop and extend `sanitise.py`
rather than editing the vendored file by hand.

- [ ] **Step 7: Write the sanitisation note**

Create `pipeline/SANITISATION.md`:

```markdown
# Sanitisation

Files under `pipeline/` are copies of code from a private repository. They are
passed through `src/amadis_htr/sanitise.py` before being committed, so that the
removal is reproducible and reviewable rather than a manual pass.

## What is removed

| removed | why |
|---|---|
| `staticData` | residue of a real 348-page production run: transcribed text, job id, run id, callback URL |
| `pinData`, `meta`, `shared` | editor state, not pipeline logic |
| workflow `id` and `versionId` | identifiers of a live workflow |
| `settings.errorWorkflow`, `settings.callerPolicy` | identifiers of a live workflow |
| node `webhookId` and `id` | a live webhook path |
| credential `id` | the credential's name is kept, so the report can say which node authenticates how |
| hosts under the private DNS zone | replaced with `example.invalid` |
| private IPv4 addresses | replaced with `0.0.0.0` |

## What is deliberately kept

Container names on the private docker network (`ocr`, `ollama`, `n8n`) stay,
because the report describes that service graph and the names are not secrets.

Every prompt, threshold, model name and code node stays. Those are the method.

## One thing the scrubbing loses

The production and preview hostnames are two distinct values and both become
`example.invalid`, so the callback allowlist in the `Validate` code node reads
`["example.invalid", "example.invalid"]`. The report quotes that block, so it
says in the caption that two distinct hosts collapsed to one placeholder. The
mechanism being described is that an exact-match allowlist exists at all, not
what is in it.

## How to re-check

```sh
grep -c 'axl-lvy\.fr\|staticData\|webhookId' pipeline/n8n/amadis-ocr.json
```

Expect no matches.
```

- [ ] **Step 8: Record the copy in PROVENANCE.md**

In `PROVENANCE.md`, under "Copied files", add the row:

```markdown
| `n8n/workflows/Q9jEMd6zCv9stSvV.json` | `pipeline/n8n/amadis-ocr.json` | `4672c91` | yes |
```

- [ ] **Step 9: Commit**

```bash
cd /home/axel/IdeaProjects/amadis-htr
git add src/amadis_htr/sanitise.py tests/test_sanitise.py pipeline/ PROVENANCE.md
git commit -m "feat: scripted sanitisation and the vendored n8n workflow

Strips 480 KB of production run residue, credential and workflow ids and the
private DNS zone. Prompts, thresholds and code nodes are kept, because they
are the method."
```

---

## Task 8: Gold-set guidelines and the stratified sampler

**Files:**
- Create: `src/amadis_htr/sampling.py`, `tests/test_sampling.py`, `data/gold/GUIDELINES.md`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `Candidate` dataclass with fields `page_id: str`, `livre: int`, `folio: str`, `family: str`, `provenance: str`
  - `TrainingContaminationError` exception
  - `excluded_livres(path) -> set[int]`
  - `sample(candidates, *, per_stratum, seed, excluded) -> list[Candidate]`
  - `write_manifest(selected, path)`

Context: the sampling frame depends on a file that does not exist yet. The gate is `data/gold/splits/training-pages.csv`, derived on Monday from the recovered `train.lst`, and it names every page that went into training. The Transkribus export lists `TRAINING_VALIDATION_SET_Amadis_4` (49 pages) and `_Amadis_3` (7 pages) among its collections, so some *Amadis de Gaule* pages are probably in the training corpus. The sampler therefore refuses to run without that file, rather than quietly sampling a contaminated frame.

Write the guidelines before annotating, not after. An annotation convention settled halfway through is a convention that differs across the set.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sampling.py`:

```python
import pytest

from amadis_htr.sampling import (
    Candidate,
    TrainingContaminationError,
    excluded_livres,
    sample,
    write_manifest,
)


def _candidates() -> list[Candidate]:
    out = []
    for livre, family in ((2, "A"), (4, "A"), (15, "B"), (19, "B")):
        for folio in range(1, 11):
            out.append(
                Candidate(
                    page_id=f"l{livre:02d}-f{folio:03d}",
                    livre=livre,
                    folio=str(folio),
                    family=family,
                    provenance="gallica" if livre > 2 else "bm-lyon",
                )
            )
    return out


def test_excluded_livres_reads_the_training_page_list(tmp_path):
    path = tmp_path / "training-pages.csv"
    path.write_text("page_id,livre\nx,4\ny,4\nz,3\n", encoding="utf-8")
    assert excluded_livres(path) == {3, 4}


def test_excluded_livres_refuses_a_missing_file(tmp_path):
    with pytest.raises(TrainingContaminationError):
        excluded_livres(tmp_path / "absent.csv")


def test_sampling_excludes_every_contaminated_livre():
    selected = sample(_candidates(), per_stratum=2, seed=1, excluded={4})
    assert all(c.livre != 4 for c in selected)


def test_sampling_covers_every_surviving_stratum():
    selected = sample(_candidates(), per_stratum=2, seed=1, excluded={4})
    strata = {(c.family, c.provenance) for c in selected}
    assert strata == {("A", "bm-lyon"), ("B", "gallica")}


def test_sampling_takes_per_stratum_not_in_total():
    selected = sample(_candidates(), per_stratum=3, seed=1, excluded=set())
    assert len(selected) == 3 * 3  # A/bm-lyon, A/gallica, B/gallica


def test_sampling_is_reproducible_under_a_seed():
    a = sample(_candidates(), per_stratum=3, seed=7, excluded=set())
    b = sample(_candidates(), per_stratum=3, seed=7, excluded=set())
    assert [c.page_id for c in a] == [c.page_id for c in b]


def test_a_different_seed_selects_differently():
    a = sample(_candidates(), per_stratum=3, seed=7, excluded=set())
    b = sample(_candidates(), per_stratum=3, seed=8, excluded=set())
    assert [c.page_id for c in a] != [c.page_id for c in b]


def test_a_small_stratum_yields_what_it_has_without_failing():
    thin = [c for c in _candidates() if c.livre != 15][:21]
    selected = sample(thin, per_stratum=50, seed=1, excluded=set())
    assert len(selected) == len(thin)


def test_selection_is_sorted_so_the_manifest_is_stable():
    selected = sample(_candidates(), per_stratum=3, seed=7, excluded=set())
    assert [c.page_id for c in selected] == sorted(c.page_id for c in selected)


def test_manifest_has_a_header_and_one_row_per_page(tmp_path):
    out = tmp_path / "MANIFEST.csv"
    write_manifest(sample(_candidates(), per_stratum=2, seed=1, excluded=set()), out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "page_id,livre,folio,family,provenance,stratum"
    assert len(lines) == 1 + 6
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_sampling.py -v
```

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'amadis_htr.sampling'`.

- [ ] **Step 3: Write the implementation**

Create `src/amadis_htr/sampling.py`:

```python
"""Seeded stratified sampling of the out-of-domain gold pages.

The frame is gated on `data/gold/splits/training-pages.csv`, derived from the
recovered `train.lst`. Some Amadis de Gaule pages are probably in the training
corpus, so the sampler refuses to run without that file rather than quietly
sampling a contaminated frame.
"""

import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


class TrainingContaminationError(RuntimeError):
    """Raised when the training page list is absent, so contamination is unknown."""


@dataclass(frozen=True)
class Candidate:
    page_id: str
    livre: int
    folio: str
    family: str
    provenance: str

    @property
    def stratum(self) -> str:
        return f"{self.family}/{self.provenance}"


def excluded_livres(path: str | Path) -> set[int]:
    """Every Livre that contributed a page to training."""
    path = Path(path)
    if not path.exists():
        raise TrainingContaminationError(
            f"{path} is missing. Derive it from the recovered train.lst before "
            "sampling: without it there is no way to know which Livres the model "
            "already saw."
        )
    with open(path, encoding="utf-8", newline="") as handle:
        return {int(row["livre"]) for row in csv.DictReader(handle) if row["livre"]}


def sample(
    candidates: Sequence[Candidate],
    *,
    per_stratum: int,
    seed: int,
    excluded: set[int],
) -> list[Candidate]:
    """Draw up to `per_stratum` pages from each stratum, reproducibly."""
    eligible = [c for c in candidates if c.livre not in excluded]

    strata: dict[str, list[Candidate]] = {}
    for candidate in eligible:
        strata.setdefault(candidate.stratum, []).append(candidate)

    selected: list[Candidate] = []
    for name in sorted(strata):
        pool = sorted(strata[name], key=lambda c: c.page_id)
        rng = random.Random(f"{seed}:{name}")
        selected.extend(rng.sample(pool, min(per_stratum, len(pool))))

    return sorted(selected, key=lambda c: c.page_id)


def write_manifest(selected: Iterable[Candidate], path: str | Path) -> None:
    """Write the gold-set manifest, one row per sampled page."""
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["page_id", "livre", "folio", "family", "provenance", "stratum"]
        )
        for c in selected:
            writer.writerow([c.page_id, c.livre, c.folio, c.family, c.provenance,
                             c.stratum])
```

- [ ] **Step 4: Run the tests**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest tests/test_sampling.py -v
```

Expected: PASS, 10 tests.

- [ ] **Step 5: Write the annotation guidelines**

Create `data/gold/GUIDELINES.md`:

```markdown
# Gold set annotation guidelines

Written before annotation begins. A convention settled halfway through is a
convention that differs across the set.

One annotator. Three pages are re-annotated blind after at least a week, and
the character error rate between the two passes is reported as the gold set's
own noise floor. No system difference smaller than that floor is claimed.

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
- **Accents follow the print.** Do not add modern accents the compositor did
  not set, and do not remove the ones he did.
- **Spelling is never modernised.** `nostre`, `estoit`, `troysiesme` and
  `aultres` are transcribed as printed. This is the single most important rule:
  the corpus's orthography is the object of study.

## Line and layout convention

- One reference line per printed line. Do not join lines that the compositor
  broke.
- A word broken across a line end keeps its hyphen as printed, including the
  `¬` form. Do not weld the halves.
- Running heads, catchwords, signatures and folio numbers are transcribed and
  labelled with their role, not omitted. The role labels are what E3 scores.
- Illegible characters are marked `�`, one per illegible character. A line that
  is more than half illegible is excluded from the gold set and the exclusion is
  recorded in `MANIFEST.csv`.

## What is excluded from the frame

Front matter, privilege leaves, tables of contents, and pages more than half
occupied by a woodcut. Those are layout problems rather than recognition
problems, and the report says so rather than letting them depress a recognition
figure.
```

- [ ] **Step 6: Run the whole suite**

```bash
cd /home/axel/IdeaProjects/amadis-htr && uv run --extra dev pytest -v
```

Expected: PASS, 69 tests across 7 files.

- [ ] **Step 7: Commit**

```bash
cd /home/axel/IdeaProjects/amadis-htr
git add src/amadis_htr/sampling.py tests/test_sampling.py data/gold/GUIDELINES.md
git commit -m "feat: gold-set annotation guidelines and the stratified sampler

The sampler refuses to run without the training page list, because some Amadis
de Gaule pages are probably in the training corpus and a contaminated frame
would be invisible. Guidelines are written before annotation, not after."
```

---

## What this plan deliberately does not do

Each item below is blocked on the artefact recovery, and each has a named
successor task in the next plan.

| not built here | blocked on |
|---|---|
| E1 recognition runs | the recovered checkpoint, the gold pages, a CUDA box |
| E2 correction grid | an Ollama instance and the recovered `val48` pages |
| E3 coherence scoring | role labels, which need the gold set annotated |
| E4 drop-cap scoring | drop-cap labels, same |
| E6 throughput | the recovered `run.json` and `calibration.json` files |
| `data/runs/matcher/alignments.csv` | database access and the user's go-ahead |
| `data/gold/splits/training-pages.csv` | the recovered `train.lst` |
| gate G1, the Juxtalinéaire docx checked against the training pages | the recovered `train.lst`, and the docx piece numbering map (docx numbers run +3 ahead of the xlsx rows from piece 120 onward) |
| gate G2, every gold page confirmed absent from training | the gold set existing, which needs G3 first |
| the LaTeX report and the Beamer deck | no LaTeX engine is installed, and there are no results to typeset |
| `src/amadis_htr/report_macros.py`, turning `eval/results/*.csv` into `\newcommand` macros and `booktabs` tables | the result CSVs existing |
| the matplotlib figure scripts under `figures/` | the result CSVs existing |
| the Hugging Face model card | confirmation of which checkpoint shipped |
| the GitHub repository | the user's go-ahead to publish |

The harness is written first so that recovery day is spent recovering, not
writing scorers.


---

## What changed during execution

Executed inline on 2026-09-18, branch `feat/evaluation-harness`. All eight tasks
landed. Three deltas between the plan and what shipped, recorded here because
the spec and the plan are the public record of method and must not contradict
the code.

**1. Task 7's key handling became a whitelist.** The plan's `_DROP_TOP_LEVEL`
list was derived from a description of an older n8n export. The real file at
`home-lab@4672c91` carries a newer shape, and the first vendoring attempt
leaked three things the plan's blacklist did not name:

- the **bare private zone** in a source comment ("both under `<zone>`, DNS we
  own"). The plan's domain pattern required a subdomain label, so it walked
  past the zone on its own. The pattern now makes the subdomain optional.
- **newer instance-state keys**: `activeVersionId` (which is the version UUID
  the plan thought it had dropped as `versionId`), `sourceWorkflowId`,
  `versionCounter`, `versionMetadata`, `createdAt`, `updatedAt`, `triggerCount`,
  `isArchived`, `active`, `tags`. Top-level keys are now a whitelist of `name`,
  `description`, `nodes`, `connections` and `settings`, so a future export
  cannot leak whatever it adds next.
- **`nodeGroups`**, which the plan did not know about. Each group carries its
  own UUID and the UUIDs of its member nodes, alongside a `name` and
  `description` that caption the pipeline usefully. The captions are kept and
  the identifiers dropped.

Four tests were added for these. The leak check in Step 6 found all three, which
is the check working rather than failing.

**2. The sanitised file is 62,442 bytes, not "well under 30,000".** The plan's
estimate was wrong. 488,639 bytes in, and the 480 KB of `staticData` is indeed
gone; what remains is 30 nodes of real Code node source, which is the method and
is meant to be there.

**3. No `.gitkeep` placeholders.** Task 1 step 6 created twelve empty files to
hold the directory skeleton, because git tracks files rather than directories.
They rendered as twelve "whitespace-only changes" entries in the bootstrap pull
request, for no benefit: the reason the directories had to pre-exist was that
the four CSV writers opened a path without creating its parent. The writers now
call `Path(path).parent.mkdir(parents=True, exist_ok=True)`, which is the real
fix, and the placeholders are gone. A directory that nothing writes to does not
need to exist in a clean checkout.

**4. Test count is 74, not 69**, the difference being four sanitiser tests and one
asserting a writer creates its own output directory. The per-task expectations up to Task 6 (13, 6, 10, 10, and 49 cumulative)
all matched exactly.

Unchanged and worth restating: the reference workbook parsed to precisely the
counts the plan predicted, 422 certain, 4 conjectures, 10 uncertain and 21 with
no usable reference, over 457 pieces.

## Where Monday's recovery lands

Two files the code already reads, neither of which can be produced on this
machine:

| file | header | unblocks |
|---|---|---|
| `data/gold/splits/training-pages.csv` | `page_id,livre` | the sampler, gate G3, and therefore the whole gold set |
| `data/runs/matcher/alignments.csv` | `piece,livre,chapter,start,end,score` | E5, the summary and the threshold sweep |

### What actually landed, 2026-09-20

`data/gold/splits/training-pages.csv` landed with the header
`page_id,livre,split`, one column wider than the plan's `page_id,livre`.
`excluded_livres()` reads it through `csv.DictReader` and ignores the extra
column, and the widening is what the artefacts turned out to require: the 48
validation pages drove checkpoint selection, so they are as seen by the model
as the 439 training pages are, and a file that named only the 439 would
understate what the fine-tune read. `livre` is empty on all 487 rows, because
no *Amadis de Gaule* page was in training. The derivation, the seed proof and
the per-collection accounting are in
`docs/notes/2026-09-20-artefact-recovery.md`.

`data/runs/matcher/alignments.csv` did not land. It needs database access and
an explicit go-ahead, and neither was in scope on recovery day.

Superseded on 2026-09-21: the sampler no longer refuses to run and no longer
excludes a Livre. Both works are the target domain, so the frame is all 24 books
minus the pages the model read, and `excluded_livres` became
`pages_the_model_saw`. Task 8's tests were rewritten accordingly.

## After the harness, still before Monday

Three things the recovery does not gate, done on 2026-09-18 on
`feat/juxtalineaire-map`:

| what | where | note |
|---|---|---|
| the Juxtalinéaire piece map, gate G1's mapping-as-code | `src/amadis_htr/juxtalineaire.py`, `eval/derive_juxtalineaire_map.py`, `data/localisation/juxtalineaire-map.csv` | the spec's remembered `+3 from piece 120` was wrong and is corrected in section 8 |
| `eval/results` CSVs into LaTeX macros and tables | `src/amadis_htr/report_macros.py` | only the localisation registry is declared, because it is the only schema that exists |
| the LaTeX skeleton and a proved toolchain | `report/`, `slides/`, `Makefile` | Tectonic 0.17 in `~/.local/bin`, Libertinus, no missing character |

Gate G1 is not closed by this. The map is the half that does not need the big
PC. The other half, cross-checking the mapped pieces against the 439 training
pages, still waits on `train.lst`.
