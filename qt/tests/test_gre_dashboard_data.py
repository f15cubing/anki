# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
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
