"""Seeded stratified sampling of the out-of-domain gold pages.

The frame is gated on `data/gold/splits/training-pages.csv`, re-derived from
the Transkribus exports on 2026-09-20. That file is what settles which Livres
the model saw, and it records none: every training and validation page is a
Trésor des Amadis T.1 page. The sampler still refuses to run without it, so
that a frame is never sampled while contamination is merely assumed.
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
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["page_id", "livre", "folio", "family", "provenance", "stratum"]
        )
        for c in selected:
            writer.writerow(
                [c.page_id, c.livre, c.folio, c.family, c.provenance, c.stratum]
            )
