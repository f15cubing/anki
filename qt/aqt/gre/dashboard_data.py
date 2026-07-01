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
