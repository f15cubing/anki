# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Faithful GRE Math Subject Test exam mode — pure form assembly + scoring.

No aqt/anki imports: kept importable headless so it is unit-testable, mirroring
`dashboard_data.py`. Assembles a deterministic, blueprint-matched (ETS 50/25/25),
leakage-isolated timed form from the **vendored** eval items (`exam_items.json`,
drift-guarded against `eval/bank/items.yaml`) and scores it rights-only with a
per-leaf breakdown. Performance/Readiness scoring happens downstream, never here.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

_ITEMS_PATH = Path(__file__).with_name("exam_items.json")

# Official computer-delivered GRE Math Subject Test: 66 items / 2h50m.
FULL_ITEMS = 66
FULL_SECONDS = 170 * 60  # 2h50m
PACE_SECONDS_PER_ITEM = FULL_SECONDS / FULL_ITEMS  # ≈ 154.5 s ≈ 2.58 min

# Pace-preserving presets (same seconds/item, fewer items — still speeded).
PRESETS = {"full": 66, "half": 33, "third": 22, "mini": 11}

# ETS content blueprint.
BLUEPRINT = {"calculus": 0.50, "algebra": 0.25, "additional": 0.25}


class InsufficientItemsError(ValueError):
    """The bank cannot satisfy the requested blueprint for this size."""


def load_exam_items(partition: str | None = None) -> list[dict]:
    """Load the vendored eval items (optionally filtered to one partition)."""
    data = json.loads(_ITEMS_PATH.read_text(encoding="utf-8"))
    items = data["items"]
    if partition is not None:
        items = [i for i in items if i["partition"] == partition]
    return items


def preset_seconds(size: int) -> int:
    """Total clock for a form of `size` items, holding the official pace."""
    return round(size * PACE_SECONDS_PER_ITEM)


def bucket_of(leaf_tag: str) -> str:
    """`topic::calculus::integral_single` -> `calculus`."""
    parts = str(leaf_tag).split("::")
    if len(parts) < 2:
        raise ValueError(f"exam: leaf tag {leaf_tag!r} has no bucket")
    return parts[1]


def blueprint_counts(
    size: int, weights: dict[str, float] | None = None
) -> dict[str, int]:
    """Apportion `size` across buckets by weight (largest-remainder, sums to size)."""
    weights = weights or BLUEPRINT
    raw = {b: size * w for b, w in weights.items()}
    counts = {b: int(math.floor(v)) for b, v in raw.items()}
    remainder = size - sum(counts.values())
    order = sorted(weights, key=lambda b: (raw[b] - counts[b], b), reverse=True)
    for b in order[:remainder]:
        counts[b] += 1
    return counts


def assemble_form(
    items: list[dict],
    size: int,
    *,
    seed: int,
    weights: dict[str, float] | None = None,
) -> list[dict]:
    """Return a deterministic, blueprint-matched form of `size` distinct items.

    Sampling is seeded (byte-stable for a fixed seed); the presentation order is
    shuffled with the same RNG. Raises `InsufficientItemsError` if a bucket lacks
    enough items.
    """
    weights = weights or BLUEPRINT
    counts = blueprint_counts(size, weights)

    pools: dict[str, list[dict]] = {b: [] for b in weights}
    for item in items:
        b = bucket_of(item["leaf_tag"])
        if b in pools:
            pools[b].append(item)

    rng = random.Random(seed)
    chosen: list[dict] = []
    for bucket in sorted(weights):
        need = counts[bucket]
        pool = sorted(pools[bucket], key=lambda it: it["id"])
        if need > len(pool):
            raise InsufficientItemsError(
                f"need {need} {bucket} items, bank has {len(pool)}"
            )
        chosen.extend(rng.sample(pool, need))

    rng.shuffle(chosen)
    return chosen


def wilson_interval(
    correct: int, total: int, z: float = 1.96
) -> tuple[float, float, float]:
    """(point, low, high) — point proportion + Wilson score CI; total<=0 -> zeros."""
    if total <= 0:
        return (0.0, 0.0, 0.0)
    p = correct / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = (z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))) / denom
    return (p, max(0.0, center - half), min(1.0, center + half))


def is_correct(item: dict, chosen: int | None) -> bool:
    """Rights-only: correct iff the chosen option index equals the key. None -> wrong."""
    return chosen is not None and chosen == item["correct_index"]


def score_form(items: list[dict], answers: dict[str, int | None]) -> dict:
    """Rights-only score + per-leaf / per-bucket breakdown + Wilson CI.

    `answers` maps item id -> chosen option index (or None / missing for omitted).
    Omitted and wrong both count as not-correct (no negative marking).
    """
    total = len(items)
    correct = 0
    by_leaf: dict[str, list[int]] = {}
    by_bucket: dict[str, list[int]] = {}
    for item in items:
        chosen = answers.get(item["id"])
        ok = is_correct(item, chosen)
        correct += 1 if ok else 0
        leaf = item["leaf_tag"]
        by_leaf.setdefault(leaf, [0, 0])
        by_leaf[leaf][0] += 1 if ok else 0
        by_leaf[leaf][1] += 1
        bucket = bucket_of(leaf)
        by_bucket.setdefault(bucket, [0, 0])
        by_bucket[bucket][0] += 1 if ok else 0
        by_bucket[bucket][1] += 1

    point, low, high = wilson_interval(correct, total)
    answered = sum(1 for it in items if answers.get(it["id"]) is not None)
    return {
        "correct": correct,
        "total": total,
        "answered": answered,
        "omitted": total - answered,
        "proportion": {"point": point, "low": low, "high": high},
        "by_leaf": {k: {"correct": v[0], "total": v[1]} for k, v in by_leaf.items()},
        "by_bucket": {
            k: {"correct": v[0], "total": v[1]} for k, v in by_bucket.items()
        },
    }


def attempts_record(
    items: list[dict],
    answers: dict[str, int | None],
    latencies: dict[str, float] | None = None,
) -> list[dict]:
    """Per-item attempts for the scoring layer to ingest (never scored here)."""
    latencies = latencies or {}
    out = []
    for item in items:
        chosen = answers.get(item["id"])
        out.append(
            {
                "item_id": item["id"],
                "leaf": item["leaf_tag"],
                "difficulty": item.get("difficulty"),
                "chosen": chosen,
                "correct": is_correct(item, chosen),
                "latency_s": latencies.get(item["id"]),
            }
        )
    return out
