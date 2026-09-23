import struct
from pathlib import Path

import pytest

from amadis_htr.training import (
    read_checkpoint_names,
    read_scalars,
    read_validation,
    summarise_run,
    write_curve,
    write_runs,
)

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "data/runs/training"


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        byte, n = n & 0x7F, n >> 7
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _field(number: int, payload: bytes) -> bytes:
    return _varint(number << 3 | 2) + _varint(len(payload)) + payload


def _event(step: int, **scalars: float) -> bytes:
    values = b"".join(
        _field(1, _field(1, tag.encode()) + _varint(2 << 3 | 5) + struct.pack("<f", v))
        for tag, v in scalars.items()
    )
    body = _varint(2 << 3) + _varint(step) + _field(5, values)
    # The CRCs are not checked by the reader, so zeros stand in for them.
    return struct.pack("<Q", len(body)) + b"\0" * 4 + body + b"\0" * 4


def _log(tmp_path, *events: bytes) -> Path:
    path = tmp_path / "events.out.tfevents.test"
    path.write_bytes(b"".join(events))
    return path


def test_scalars_are_read_by_tag_and_step(tmp_path):
    path = _log(tmp_path, _event(10, epoch=0.0), _event(10, val_accuracy=0.99))
    scalars = read_scalars(path)
    assert scalars["epoch"] == [(10, 0.0)]
    assert scalars["val_accuracy"][0][0] == 10
    assert scalars["val_accuracy"][0][1] == pytest.approx(0.99)


def test_the_curve_is_keyed_by_epoch_and_cer_is_one_minus_accuracy(tmp_path):
    path = _log(
        tmp_path,
        _event(196, epoch=0.0, val_accuracy=0.98, val_word_accuracy=0.9),
        _event(393, epoch=1.0, val_accuracy=0.99, val_word_accuracy=0.95),
    )
    curve = read_validation("r", path)
    assert [e.epoch for e in curve] == [0, 1]
    assert curve[1].cer == pytest.approx(0.01)
    assert curve[1].wer == pytest.approx(0.05)


def test_a_val_cer_that_disagrees_with_the_accuracy_is_refused(tmp_path):
    # val_cer is logged one ahead of the epoch, so counter 1 is epoch 0.
    path = _log(
        tmp_path,
        _event(196, epoch=0.0, val_accuracy=0.98),
        _event(1, val_cer=0.03),
    )
    with pytest.raises(ValueError, match="disagrees"):
        read_validation("r", path)


def test_a_restarted_epoch_keeps_its_later_checkpoint():
    names = ["checkpoint_00-0.9880.ckpt", "checkpoint_00-0.9883.ckpt",
             "checkpoint_01-0.9894.ckpt", "checkpoint_abort.ckpt"]
    curve = read_checkpoint_names("r", names)
    assert [e.epoch for e in curve] == [0, 1]
    assert curve[0].cer == pytest.approx(0.0117)


def test_the_shipped_checkpoint_is_the_one_the_run_selected():
    # PROVENANCE.md names checkpoint_55-0.9950.ckpt as the export source; the
    # log has to agree with the file name kraken gave it.
    (log,) = (RUNS / "rop0.5-lr3e-4-augment").glob("events.out.tfevents.*")
    row = summarise_run(read_validation("shipped", log))
    assert row.best_epoch == 55
    assert round(1 - row.cer, 4) == 0.9950


def test_the_committed_results_regenerate_from_the_committed_inputs(tmp_path):
    (log,) = (RUNS / "rop0.5-lr3e-4-augment").glob("events.out.tfevents.*")
    shipped = read_validation("rop0.5-lr3e-4-augment", log)
    names = (RUNS / "run1-constant-lr0.001/checkpoints.txt").read_text().splitlines()
    constant = read_checkpoint_names("run1-constant-lr0.001", names)
    write_curve(shipped + constant, tmp_path / "training-curve.csv")
    write_runs([summarise_run(shipped), summarise_run(constant)],
               tmp_path / "training-runs.csv")
    for name in ("training-curve.csv", "training-runs.csv"):
        committed = REPO / "eval/results" / name
        assert (tmp_path / name).read_bytes() == committed.read_bytes(), name
