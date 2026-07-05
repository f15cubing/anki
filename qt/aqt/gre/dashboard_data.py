# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Pure view-model for the GRE desktop dashboard (W2).

No aqt/anki imports: it maps W1 MasteryQuery rows onto the frozen GRE taxonomy
and computes the Memory range (Wilson), 50/25/25 rollups, coverage, and the
next-best topic. Kept importable headless so it is unit-testable.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

_TAXONOMY_PATH = Path(__file__).with_name("taxonomy.json")


@dataclass(frozen=True)
class Bucket:
    name: str
    weight: float
    leaves: tuple[str, ...]


@dataclass(frozen=True)
class Taxonomy:
    tag_prefix: str
    tag_sep: str
    buckets: tuple[Bucket, ...]


def load_taxonomy() -> Taxonomy:
    raw = json.loads(_TAXONOMY_PATH.read_text(encoding="utf-8"))
    buckets = tuple(
        Bucket(name=b["name"], weight=float(b["weight"]), leaves=tuple(b["leaves"]))
        for b in raw["buckets"]
    )
    return Taxonomy(tag_prefix=raw["tag_prefix"], tag_sep=raw["tag_sep"], buckets=buckets)


def leaf_tag(bucket: str, leaf: str, tax: Taxonomy | None = None) -> str:
    tax = tax or load_taxonomy()
    return tax.tag_sep.join((tax.tag_prefix, bucket, leaf))


def bucket_tag(bucket: str, tax: Taxonomy | None = None) -> str:
    tax = tax or load_taxonomy()
    return tax.tag_sep.join((tax.tag_prefix, bucket))


def all_leaf_tags(tax: Taxonomy | None = None) -> list[str]:
    tax = tax or load_taxonomy()
    return [leaf_tag(b.name, leaf, tax) for b in tax.buckets for leaf in b.leaves]


def all_bucket_tags(tax: Taxonomy | None = None) -> list[str]:
    tax = tax or load_taxonomy()
    return [bucket_tag(b.name, tax) for b in tax.buckets]


def query_topics(tax: Taxonomy | None = None) -> list[str]:
    tax = tax or load_taxonomy()
    return all_leaf_tags(tax) + all_bucket_tags(tax)


def wilson_interval(mastered: int, reviewed: int, z: float = 1.96) -> tuple[float, float, float]:
    """(point, low, high). point = raw proportion; [low,high] = Wilson score CI."""
    if reviewed <= 0:
        return (0.0, 0.0, 0.0)
    n = reviewed
    p = mastered / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (p, max(0.0, center - half), min(1.0, center + half))


def headline(bucket_points: list[dict], z: float = 1.96) -> dict | None:
    """ETS-weighted (50/25/25) headline over buckets that have reviews.

    Buckets with reviewed==0 are excluded and remaining weights renormalized.
    Interval via weighted normal error propagation over the pooled proportions.
    """
    present = [b for b in bucket_points if b["reviewed"] > 0]
    if not present:
        return None
    wsum = sum(b["weight"] for b in present)
    point = sum((b["weight"] / wsum) * b["point"] for b in present)
    var = 0.0
    for b in present:
        w = b["weight"] / wsum
        p = b["point"]
        var += w * w * p * (1 - p) / b["reviewed"]
    se = math.sqrt(var)
    return {
        "point": point,
        "low": max(0.0, point - z * se),
        "high": min(1.0, point + z * se),
        "buckets_reflected": len(present),
        "buckets_total": len(bucket_points),
    }


def _memory_cell(row) -> dict:
    point, low, high = wilson_interval(row.mastered_count, row.reviewed_count)
    return {
        "point": point, "low": low, "high": high,
        "reviewed": row.reviewed_count, "total": row.total_cards,
        "mean_r": row.avg_recall,
    }


def load_exam_attempts(path: str | Path) -> list[dict]:
    """Flatten the exam-results side-file into one pooled per-item attempts list.

    The file (written by the Exam Mode submit handler) is JSON-lines: one object
    per session, each with an ``attempts`` array of per-item records that carry a
    boolean ``correct``. Best-effort: a missing/unreadable file or any malformed
    line yields no rows rather than raising into the dashboard response path.
    """
    out: list[dict] = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, ValueError):
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        for attempt in record.get("attempts", []) or []:
            if isinstance(attempt, dict) and "correct" in attempt:
                out.append(attempt)
    return out


def observed_performance(attempts: list[dict]) -> dict:
    """Observed rights-only accuracy across timed exam items, as a range.

    This is the *observed* Performance surface: the learner's measured accuracy
    on our authored, ETS-firewalled practice items — honest at low n. It is
    deliberately NOT the calibrated logistic+Platt projection from
    ``scoring/performance.py`` (that model needs a multi-student attempt corpus;
    fitting it on one learner's handful of attempts would look confident exactly
    when it knows least). Honesty ceilings: always a range with ``n`` via the
    Wilson score interval, never a bare point; with no attempts we report a
    give-up state, never a fabricated 0.
    """
    graded = [a for a in attempts if isinstance(a, dict) and "correct" in a]
    total = len(graded)
    if total == 0:
        return {
            "state": "not_available",
            "note": "Take a timed exam (Tools \u25b8 GRE exam mode) to measure performance.",
        }
    correct = sum(1 for a in graded if a["correct"])
    point, low, high = wilson_interval(correct, total)
    plural = "s" if total != 1 else ""
    return {
        "state": "observed",
        "correct": correct,
        "total": total,
        "point": point,
        "low": low,
        "high": high,
        "note": (
            f"Observed accuracy across {total} timed item{plural} from your "
            "authored practice bank (not ETS) \u2014 a range, not a projected score."
        ),
    }


def next_best_topic(rows_by_tag: dict, tax: Taxonomy) -> str | None:
    leaves = [(b, leaf, leaf_tag(b.name, leaf, tax)) for b in tax.buckets for leaf in b.leaves]
    # 1) highest exam-weight uncovered leaf; ties -> taxonomy order
    uncovered = [(b, tag) for (b, _leaf, tag) in leaves if rows_by_tag[tag].reviewed_count == 0]
    if uncovered:
        uncovered.sort(key=lambda bt: -bt[0].weight)  # stable -> preserves taxonomy order in ties
        return uncovered[0][1]
    # 2) all studied -> lowest memory lower-bound; ties -> taxonomy order
    best_tag, best_low = None, 2.0
    for (_b, _leaf, tag) in leaves:
        _, low, _ = wilson_interval(rows_by_tag[tag].mastered_count, rows_by_tag[tag].reviewed_count)
        if low < best_low:
            best_low, best_tag = low, tag
    return best_tag


def build_view_model(
    rows_by_tag: dict, *, generated_at: str, exam_attempts: list | None = None
) -> dict:
    tax = load_taxonomy()
    # buckets
    bucket_vms, bucket_points = [], []
    for b in tax.buckets:
        row = rows_by_tag[bucket_tag(b.name, tax)]
        cell = _memory_cell(row)
        bucket_points.append({"weight": b.weight, "point": cell["point"], "reviewed": row.reviewed_count})
        bucket_vms.append({"bucket": b.name, "weight": b.weight, **cell})
    # leaves + coverage
    leaf_vms, deck, studied = [], 0, 0
    for b in tax.buckets:
        for leaf in b.leaves:
            tag = leaf_tag(b.name, leaf, tax)
            row = rows_by_tag[tag]
            if row.total_cards > 0:
                deck += 1
            if row.reviewed_count > 0:
                studied += 1
            leaf_vms.append({
                "tag": tag, "bucket": b.name, "leaf": leaf,
                "has_cards": row.total_cards > 0,
                "studied": row.reviewed_count > 0,
                "memory": _memory_cell(row) if row.reviewed_count > 0 else None,
            })
    n_leaves = len(leaf_vms)
    studied_pct = studied / n_leaves if n_leaves else 0.0
    reasons = []
    if studied_pct < 0.50:
        reasons.append("<50% studied coverage")
    total_reviewed = sum(rows_by_tag[bucket_tag(b.name, tax)].reviewed_count for b in tax.buckets)
    if total_reviewed < 200:
        reasons.append("<200 graded reviews")
    return {
        "generated_at": generated_at,
        "memory": {"headline": headline(bucket_points), "buckets": bucket_vms},
        "coverage": {
            "deck_pct": deck / n_leaves if n_leaves else 0.0,
            "studied_pct": studied_pct,
            "leaves": leaf_vms,
        },
        "readiness": {
            "state": "insufficient_evidence",
            "studied_pct": studied_pct,
            "next_best_topic": next_best_topic(rows_by_tag, tax),
            "reasons": reasons,
        },
        "performance": observed_performance(exam_attempts or []),
    }
