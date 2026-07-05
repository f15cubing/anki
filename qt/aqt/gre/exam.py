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

# Timed Exam Mode is mastery-gated (PRD §8a): a timed mock helps prepared learners and
# wastes under-prepared ones, so it stays locked until the learner has studied enough of
# the exam. "Studied coverage" = fraction of the 17 ETS leaf topics with >=1 graded
# review (see dashboard_data.studied_coverage). Independent of the readiness give-up gate.
MIN_STUDIED_COVERAGE = 0.70


def coverage_meets_threshold(
    studied: int, total: int, threshold: float = MIN_STUDIED_COVERAGE
) -> bool:
    """True iff studied/total >= threshold. Zero topics is never unlocked."""
    if total <= 0:
        return False
    return (studied / total) >= threshold


def coverage_lock_reason(
    studied: int, total: int, threshold: float = MIN_STUDIED_COVERAGE
) -> str:
    """Friendly explanation of why Exam Mode is locked and what unlocks it."""
    pct = round((studied / total) * 100) if total else 0
    need = math.ceil(threshold * total) if total else 0
    remaining = max(0, need - studied)
    return (
        f"Exam Mode unlocks once you've studied {round(threshold * 100)}% of the "
        f"{total} exam topics. You've studied {studied} ({pct}%) — study "
        f"{remaining} more topic{'s' if remaining != 1 else ''} to start a timed mock."
    )


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


def bucket_pool_sizes(
    items: list[dict], weights: dict[str, float] | None = None
) -> dict[str, int]:
    """Per-bucket count of available items (only buckets named in the blueprint)."""
    weights = weights or BLUEPRINT
    pools = {b: 0 for b in weights}
    for item in items:
        b = bucket_of(item["leaf_tag"])
        if b in pools:
            pools[b] += 1
    return pools


def size_is_feasible(
    items: list[dict], size: int, weights: dict[str, float] | None = None
) -> bool:
    """True iff a blueprint-matched form of exactly `size` items can be drawn.

    This is the cheap pre-check the exam endpoints use so a preset that the
    firewalled bank cannot satisfy is never offered (rather than failing after
    the user picks it). `size <= 0` is never feasible.
    """
    weights = weights or BLUEPRINT
    if size <= 0:
        return False
    counts = blueprint_counts(size, weights)
    pools = bucket_pool_sizes(items, weights)
    return all(counts[b] <= pools.get(b, 0) for b in counts)


def max_feasible_size(
    items: list[dict],
    weights: dict[str, float] | None = None,
    cap: int = FULL_ITEMS,
) -> int:
    """Largest blueprint-matched form size in ``0..cap`` the pool supports (0 if none).

    The blueprint apportionment is not perfectly monotonic in `size`, so we scan
    from `cap` downward and return the first size that fits every bucket pool.
    """
    for size in range(cap, 0, -1):
        if size_is_feasible(items, size, weights):
            return size
    return 0


def feasible_presets(
    items: list[dict], weights: dict[str, float] | None = None
) -> list[dict]:
    """Each named preset annotated with whether the current pool can build it."""
    return [
        {
            "id": preset_id,
            "items": size,
            "seconds": preset_seconds(size),
            "feasible": size_is_feasible(items, size, weights),
        }
        for preset_id, size in PRESETS.items()
    ]


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
