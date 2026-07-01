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
