"""Seeded stratified sampling of pages, and the training split it subtracts.

E2 draws its 400 pages with `sample`, 200 per type family under a seed fixed in
the pre-registration. `pages_the_model_saw` reads the other half of the job:
`data/gold/splits/training-pages.csv` lists the 487 pages the recogniser trained
on, all of them *Trésor* T.1, and `eval/build_gold_set.py` subtracts them so
that no page the model read can enter the released set.
"""

import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Candidate:
    page_id: str
    livre: int
    folio: str
    family: str
    provenance: str

    @property
    def stratum(self) -> str:
        # Provenance is recorded for four of the 24 books and for no other, so a
        # candidate may legitimately have none. Folding an empty provenance into
        # the family rather than writing `A/` keeps the stratum name honest: it
        # says the draw was stratified on family alone, which for E2 it is.
        return f"{self.family}/{self.provenance}" if self.provenance else self.family


def pages_the_model_saw(path: str | Path) -> set[str]:
    """Every page id in the training and validation split."""
    with open(path, encoding="utf-8", newline="") as handle:
        return {row["page_id"] for row in csv.DictReader(handle) if row["page_id"]}


def sample(
    candidates: Sequence[Candidate],
    *,
    per_stratum: int,
    seed: int,
    seen: frozenset[str] | set[str] = frozenset(),
) -> list[Candidate]:
    """Draw up to `per_stratum` pages from each stratum, reproducibly."""
    eligible = [c for c in candidates if c.page_id not in seen]

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
