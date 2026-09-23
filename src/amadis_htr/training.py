"""The fine-tune's validation record, read from the training run's own logs.

The shipped model was selected on validation character error rate, and until
now the report could not state that rate: the only copy of it was a checkpoint
file name and a README line. The TensorBoard event file the run wrote holds the
whole curve, one value per epoch, and is committed under `data/runs/training/`
so the figure rebuilds without the run's environment.

The event file is read here with a few dozen lines of protobuf decoding rather
than with TensorBoard, which would add a heavy dependency to read four scalar
tags. Only the parts of the `Event` and `Summary` messages that carry scalars
are decoded; everything else is skipped by wire type.

**Kraken's `val_accuracy` is one minus its character error rate.** The run logs
both, and they agree to float precision, but `val_cer` is keyed by a counter
one ahead of the epoch and is missing the last epoch. `val_accuracy` is logged
at the global step alongside `epoch`, so the curve is built from it and the
CER is its complement. `read_validation` checks the two against each other, so
a kraken release that changes either definition fails here rather than on the
page.

The earlier constant-rate run logged no validation scalars. What survives of
it is its checkpoint names, which kraken writes as `checkpoint_<epoch>-<val
accuracy>.ckpt`, and those are what `read_checkpoint_names` parses.
"""

import csv
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

_CHECKPOINT = re.compile(r"checkpoint_(\d+)-(\d\.\d+)\.ckpt")


@dataclass(frozen=True)
class Epoch:
    """One validation pass. Rates are fractions, as everywhere in the results."""

    run: str
    epoch: int
    cer: float
    wer: float | None


@dataclass(frozen=True)
class RunRow:
    """A training run summarised by the checkpoint it would ship."""

    run: str
    epochs: int
    best_epoch: int
    cer: float
    wer: float | None


def _varint(data: bytes, i: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        byte = data[i]
        i += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if byte < 0x80:
            return value, i


def _fields(data: bytes) -> Iterator[tuple[int, bytes | int]]:
    """Yield (field number, raw value) for one protobuf message."""
    i = 0
    while i < len(data):
        key, i = _varint(data, i)
        number, wire = key >> 3, key & 7
        if wire == 0:
            value, i = _varint(data, i)
        elif wire == 1:
            value, i = data[i : i + 8], i + 8
        elif wire == 5:
            value, i = data[i : i + 4], i + 4
        elif wire == 2:
            size, i = _varint(data, i)
            value, i = data[i : i + size], i + size
        else:
            raise ValueError(f"unsupported protobuf wire type {wire}")
        yield number, value


def _records(path: str | Path) -> Iterator[bytes]:
    """TFRecord framing: length, its CRC, the payload, the payload's CRC."""
    data = Path(path).read_bytes()
    i = 0
    while i < len(data):
        (size,) = struct.unpack("<Q", data[i : i + 8])
        i += 12
        yield data[i : i + size]
        i += size + 4


def read_scalars(path: str | Path) -> dict[str, list[tuple[int, float]]]:
    """Every scalar in an event file, as tag -> [(step, value)] in file order.

    `Event` carries the step in field 2 and a `Summary` in field 5; each
    `Summary.Value` has its tag in field 1 and a scalar in field 2.
    """
    scalars: dict[str, list[tuple[int, float]]] = {}
    for record in _records(path):
        step = 0
        values: list[tuple[str, float]] = []
        for number, value in _fields(record):
            if number == 2:
                step = value
            elif number == 5:
                for inner, item in _fields(value):
                    if inner != 1:
                        continue
                    tag, scalar = None, None
                    for part, content in _fields(item):
                        if part == 1:
                            tag = content.decode("utf-8")
                        elif part == 2:
                            (scalar,) = struct.unpack("<f", content)
                    if tag is not None and scalar is not None:
                        values.append((tag, scalar))
        for tag, scalar in values:
            scalars.setdefault(tag, []).append((step, scalar))
    return scalars


def read_validation(run: str, path: str | Path) -> list[Epoch]:
    """The per-epoch validation curve of one kraken run."""
    scalars = read_scalars(path)
    epoch_at = {step: int(value) for step, value in scalars["epoch"]}
    words = dict(scalars.get("val_word_accuracy", []))
    curve = [
        Epoch(
            run=run,
            epoch=epoch_at[step],
            cer=1 - accuracy,
            wer=1 - words[step] if step in words else None,
        )
        for step, accuracy in scalars["val_accuracy"]
    ]
    # val_cer[k] is epoch k - 1; see the module docstring.
    for counter, cer in scalars.get("val_cer", []):
        logged = curve[counter - 1].cer
        if abs(logged - cer) > 1e-6:
            raise ValueError(
                f"{run}: val_cer {cer:.6f} disagrees with 1 - val_accuracy "
                f"{logged:.6f} at epoch {counter - 1}"
            )
    return curve


def read_checkpoint_names(run: str, names: Iterable[str]) -> list[Epoch]:
    """A curve from checkpoint file names, for a run that logged nothing else.

    An epoch that was restarted leaves two checkpoints; the later pass is the
    one training continued from, and it is the one kept.
    """
    by_epoch: dict[int, float] = {}
    for name in names:
        match = _CHECKPOINT.fullmatch(name.strip())
        if match:
            by_epoch[int(match[1])] = 1 - float(match[2])
    return [Epoch(run, epoch, cer, None) for epoch, cer in sorted(by_epoch.items())]


def summarise_run(curve: list[Epoch]) -> RunRow:
    """The run as shipped: the epoch with the lowest validation CER.

    Ties go to the earlier epoch, which is what kraken's checkpoint selection
    does.
    """
    best = min(curve, key=lambda e: (e.cer, e.epoch))
    return RunRow(best.run, len(curve), best.epoch, best.cer, best.wer)


def write_curve(curve: Iterable[Epoch], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run", "epoch", "cer", "wer"])
        for e in curve:
            writer.writerow(
                [e.run, e.epoch, f"{e.cer:.6f}", "" if e.wer is None else f"{e.wer:.6f}"]
            )


def write_runs(runs: Iterable[RunRow], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run", "epochs", "best_epoch", "cer", "wer"])
        for r in runs:
            writer.writerow(
                [r.run, r.epochs, r.best_epoch, f"{r.cer:.6f}",
                 "" if r.wer is None else f"{r.wer:.6f}"]
            )
