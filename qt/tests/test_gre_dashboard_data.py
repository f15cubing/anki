# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from dataclasses import dataclass as _dc

import pytest

from aqt.gre import dashboard_data as dd


def test_taxonomy_has_17_leaves_and_weights_sum_to_one():
    tax = dd.load_taxonomy()
    leaves = [leaf for b in tax.buckets for leaf in b.leaves]
    assert len(leaves) == 17
    assert abs(sum(b.weight for b in tax.buckets) - 1.0) < 1e-9
    assert [b.name for b in tax.buckets] == ["calculus", "algebra", "additional"]


def test_query_topics_lists_leaf_tags_then_bucket_tags():
    topics = dd.query_topics()
    assert topics[0] == "topic::calculus::differential_single"
    assert topics[16] == "topic::additional::numerical"
    assert topics[17:] == ["topic::calculus", "topic::algebra", "topic::additional"]


def test_wilson_zero_reviews_is_all_zero():
    assert dd.wilson_interval(0, 0) == (0.0, 0.0, 0.0)


def test_wilson_known_value():
    point, low, high = dd.wilson_interval(8, 10)
    assert point == pytest.approx(0.8)
    assert low == pytest.approx(0.490, abs=0.01)
    assert high == pytest.approx(0.943, abs=0.01)


def test_wilson_bounds_are_clamped_to_unit_interval():
    for m, n in [(0, 5), (5, 5)]:
        _, low, high = dd.wilson_interval(m, n)
        assert 0.0 <= low <= high <= 1.0


def test_headline_none_when_no_reviews():
    assert dd.headline([{"weight": 0.5, "point": 0.0, "reviewed": 0}]) is None


def test_headline_reweights_when_a_bucket_has_no_reviews():
    out = dd.headline([
        {"weight": 0.50, "point": 0.8, "reviewed": 10},
        {"weight": 0.25, "point": 0.6, "reviewed": 5},
        {"weight": 0.25, "point": 0.0, "reviewed": 0},  # excluded + renormalized
    ])
    assert out["point"] == pytest.approx(0.7333, abs=0.001)
    assert out["buckets_reflected"] == 2
    assert out["buckets_total"] == 3
    assert 0.0 <= out["low"] <= out["point"] <= out["high"] <= 1.0


@_dc
class FakeRow:
    total_cards: int = 0
    reviewed_count: int = 0
    mastered_count: int = 0
    avg_recall: float = 0.0


def _rows(**overrides):
    """All 20 topics zeroed, then apply overrides by tag."""
    rows = {t: FakeRow() for t in dd.query_topics()}
    rows.update(overrides)
    return rows


def test_empty_collection_suppresses_headline_and_gates_readiness():
    vm = dd.build_view_model(_rows(), generated_at="t")
    assert vm["memory"]["headline"] is None
    assert vm["coverage"]["deck_pct"] == 0.0
    assert vm["coverage"]["studied_pct"] == 0.0
    assert vm["readiness"]["state"] == "insufficient_evidence"
    assert vm["performance"]["state"] == "not_available"


def test_coverage_counts_deck_and_studied():
    vm = dd.build_view_model(_rows(**{
        "topic::calculus::integral_single": FakeRow(total_cards=5, reviewed_count=3, mastered_count=2, avg_recall=0.7),
        "topic::algebra::linear": FakeRow(total_cards=4, reviewed_count=0, mastered_count=0),
    }), generated_at="t")
    assert vm["coverage"]["deck_pct"] == pytest.approx(2 / 17)
    assert vm["coverage"]["studied_pct"] == pytest.approx(1 / 17)


def test_next_best_topic_prefers_highest_weight_uncovered_leaf():
    # nothing studied -> highest-weight bucket (calculus) first leaf, taxonomy order
    assert dd.next_best_topic(_rows(), dd.load_taxonomy()) == "topic::calculus::differential_single"


def test_headline_uses_bucket_rows_rolled_up_by_rpc():
    vm = dd.build_view_model(_rows(**{
        "topic::calculus": FakeRow(total_cards=100, reviewed_count=10, mastered_count=8, avg_recall=0.82),
        "topic::algebra": FakeRow(total_cards=40, reviewed_count=5, mastered_count=3, avg_recall=0.6),
    }), generated_at="t")
    assert vm["memory"]["headline"]["point"] == pytest.approx(0.7333, abs=0.001)
    assert vm["memory"]["headline"]["buckets_reflected"] == 2
