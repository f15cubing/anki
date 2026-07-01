# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pytest
from aqt.gre import dashboard_data as dd


def test_taxonomy_has_17_leaves_and_weights_sum_to_one():
    tax = dd.load_taxonomy()
    leaves = [leaf for b in tax.buckets for leaf in b.leaves]
    assert len(leaves) == 17
    assert abs(sum(b.weight for b in tax.buckets) - 1.0) < 1e-9
    assert [b.name for b in tax.buckets] == ["calculus", "algebra", "additional"]


def test_query_topics_lists_leaf_tags_then_bucket_tags():
    tax = dd.load_taxonomy()
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
