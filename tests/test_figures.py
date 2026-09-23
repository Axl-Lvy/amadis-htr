import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIGURES = REPO / "report/generated/figures"
#: The French report's copies, same data and translated labels.
FIGURES_FR = REPO / "report/generated/fr/figures"


def _regenerate():
    return subprocess.run(
        [sys.executable, "figures/make_figures.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin", "HOME": str(Path.home())},
    )


def test_a_figure_is_committed_for_every_measured_result():
    # A figure is a reported figure, so Rule 1 covers it: it is drawn from the
    # committed CSVs and never pasted in. These three have their measurements.
    # corpus-extracts and e2-reasons were drawn and then dropped on 2026-09-22:
    # two bars each, saying what the sentence beside them already said, in a
    # report cut to ten pages. Their CSVs are still written and still checked.
    for name in ("e5-sweep", "e6-throughput", "e2-confidence"):
        assert (FIGURES / f"{name}.pdf").exists(), name
        assert (FIGURES_FR / f"{name}.pdf").exists(), name


def test_the_committed_figures_redraw_byte_for_byte():
    # matplotlib stamps a CreationDate into a PDF unless it is told not to.
    # With one, a figure redrawn from unchanged inputs differs from its
    # committed copy on every run, so `git diff` after eval/run_all.sh -- the
    # repository's own drift check -- reports a change every time and
    # therefore reports nothing.
    def committed():
        return {
            p.relative_to(REPO): p.read_bytes()
            for folder in (FIGURES, FIGURES_FR)
            for p in sorted(folder.glob("*.pdf"))
        }

    before = committed()
    if not before:
        pytest.skip("no figures committed yet")

    result = _regenerate()
    assert result.returncode == 0, result.stderr

    after = committed()
    assert set(after) == set(before)
    drifted = [name for name in before if before[name] != after[name]]
    assert not drifted, (
        f"{drifted} changed on a redraw from unchanged inputs. A figure that "
        "cannot round-trip makes the drift check useless."
    )
