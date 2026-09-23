"""The fine-tune's validation curve and its selected checkpoint, per run.

Reads the shipped run's TensorBoard event file and the earlier run's checkpoint
names, both committed under `data/runs/training/`.

    uv run python eval/training_results.py
"""

from pathlib import Path

from amadis_htr.training import (
    read_checkpoint_names,
    read_validation,
    summarise_run,
    write_curve,
    write_runs,
)

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "data/runs/training"
RESULTS = REPO / "eval/results"

SHIPPED = "rop0.5-lr3e-4-augment"
CONSTANT = "run1-constant-lr0.001"


def main() -> None:
    (log,) = (RUNS / SHIPPED).glob("events.out.tfevents.*")
    shipped = read_validation(SHIPPED, log)
    names = (RUNS / CONSTANT / "checkpoints.txt").read_text(encoding="utf-8")
    constant = read_checkpoint_names(CONSTANT, names.splitlines())

    write_curve(shipped + constant, RESULTS / "training-curve.csv")
    runs = [summarise_run(shipped), summarise_run(constant)]
    write_runs(runs, RESULTS / "training-runs.csv")
    for r in runs:
        print(f"{r.run}: best epoch {r.best_epoch} of {r.epochs}, "
              f"validation CER {r.cer:.2%}")


if __name__ == "__main__":
    main()
