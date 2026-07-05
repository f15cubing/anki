# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import json
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
    out = dd.headline(
        [
            {"weight": 0.50, "point": 0.8, "reviewed": 10},
            {"weight": 0.25, "point": 0.6, "reviewed": 5},
            {"weight": 0.25, "point": 0.0, "reviewed": 0},  # excluded + renormalized
        ]
    )
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
    vm = dd.build_view_model(
        _rows(
            **{
                "topic::calculus::integral_single": FakeRow(
                    total_cards=5, reviewed_count=3, mastered_count=2, avg_recall=0.7
                ),
                "topic::algebra::linear": FakeRow(
                    total_cards=4, reviewed_count=0, mastered_count=0
                ),
            }
        ),
        generated_at="t",
    )
    assert vm["coverage"]["deck_pct"] == pytest.approx(2 / 17)
    assert vm["coverage"]["studied_pct"] == pytest.approx(1 / 17)


def test_next_best_topic_prefers_highest_weight_uncovered_leaf():
    # nothing studied -> highest-weight bucket (calculus) first leaf, taxonomy order
    assert (
        dd.next_best_topic(_rows(), dd.load_taxonomy())
        == "topic::calculus::differential_single"
    )


def test_next_best_topic_all_studied_returns_lowest_memory_lower_bound():
    # every leaf studied -> no uncovered leaf; fall through to lowest Wilson lower-bound
    tax = dd.load_taxonomy()
    rows = {
        t: FakeRow(total_cards=10, reviewed_count=10, mastered_count=9)
        for t in dd.query_topics()
    }
    weakest = "topic::algebra::linear"
    rows[weakest] = FakeRow(total_cards=10, reviewed_count=10, mastered_count=1)
    assert dd.next_best_topic(rows, tax) == weakest


def test_headline_uses_bucket_rows_rolled_up_by_rpc():
    vm = dd.build_view_model(
        _rows(
            **{
                "topic::calculus": FakeRow(
                    total_cards=100,
                    reviewed_count=10,
                    mastered_count=8,
                    avg_recall=0.82,
                ),
                "topic::algebra": FakeRow(
                    total_cards=40, reviewed_count=5, mastered_count=3, avg_recall=0.6
                ),
            }
        ),
        generated_at="t",
    )
    assert vm["memory"]["headline"]["point"] == pytest.approx(0.7333, abs=0.001)
    assert vm["memory"]["headline"]["buckets_reflected"] == 2


# --- observed Performance (from Exam Mode attempts) --------------------------


def test_observed_performance_no_attempts_is_not_available_never_zero():
    out = dd.observed_performance([])
    assert out["state"] == "not_available"
    # honesty ceiling: no fabricated point when there is no evidence
    assert "point" not in out
    assert "GRE exam mode" in out["note"]


def test_observed_performance_pools_attempts_into_a_wilson_range():
    attempts = [
        {"correct": True},
        {"correct": True},
        {"correct": False},
        {"correct": True},
    ]
    out = dd.observed_performance(attempts)
    assert out["state"] == "observed"
    assert (out["correct"], out["total"]) == (3, 4)
    assert out["point"] == pytest.approx(0.75)
    # always a range, clamped to the unit interval, bracketing the point
    assert 0.0 <= out["low"] <= out["point"] <= out["high"] <= 1.0


def test_observed_performance_ignores_malformed_entries():
    out = dd.observed_performance(
        [{"correct": True}, {"nope": 1}, "x", None, {"correct": False}]
    )
    assert (out["correct"], out["total"]) == (1, 2)


def test_build_view_model_surfaces_observed_performance_when_attempts_present():
    vm = dd.build_view_model(
        _rows(),
        generated_at="t",
        exam_attempts=[{"correct": True}, {"correct": False}],
    )
    assert vm["performance"]["state"] == "observed"
    assert vm["performance"]["total"] == 2
    assert 0.0 <= vm["performance"]["low"] <= vm["performance"]["high"] <= 1.0


def test_build_view_model_without_attempts_keeps_performance_not_available():
    vm = dd.build_view_model(_rows(), generated_at="t")
    assert vm["performance"]["state"] == "not_available"


def test_load_exam_attempts_flattens_all_sessions(tmp_path):
    p = tmp_path / "gre_exam_results.jsonl"
    p.write_text(
        json.dumps({"ts": 1, "attempts": [{"item_id": "a", "correct": True}]})
        + "\n"
        + json.dumps(
            {
                "ts": 2,
                "attempts": [
                    {"item_id": "b", "correct": False},
                    {"item_id": "c", "correct": True},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = dd.load_exam_attempts(str(p))
    assert len(out) == 3
    assert sum(1 for a in out if a["correct"]) == 2


def test_load_exam_attempts_missing_file_is_empty(tmp_path):
    assert dd.load_exam_attempts(str(tmp_path / "nope.jsonl")) == []


def test_load_exam_attempts_skips_malformed_lines(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text(
        "not json\n" + json.dumps({"attempts": [{"correct": True}]}) + "\n" + "\n",
        encoding="utf-8",
    )
    assert len(dd.load_exam_attempts(str(p))) == 1


def test_load_then_observe_end_to_end(tmp_path):
    p = tmp_path / "gre_exam_results.jsonl"
    p.write_text(
        json.dumps(
            {"attempts": [{"correct": True}, {"correct": True}, {"correct": False}]}
        )
        + "\n",
        encoding="utf-8",
    )
    out = dd.observed_performance(dd.load_exam_attempts(str(p)))
    assert (out["state"], out["correct"], out["total"]) == ("observed", 2, 3)


# --- Home additions: coverage, study-next, stats, labels --------------------


def test_leaf_label_known_and_prettified_fallback():
    assert dd.leaf_label("integral_single") == "Single-variable integral calculus"
    assert dd.leaf_label("mystery_leaf") == "Mystery leaf"


def test_studied_coverage_counts_leaves_with_reviews():
    cov = dd.studied_coverage(
        _rows(
            **{
                "topic::calculus::integral_single": FakeRow(
                    total_cards=5, reviewed_count=3, mastered_count=2
                ),
                "topic::algebra::linear": FakeRow(total_cards=4, reviewed_count=0),
            }
        ),
        dd.load_taxonomy(),
    )
    assert cov["studied"] == 1
    assert cov["total"] == 17
    assert cov["pct"] == pytest.approx(1 / 17)


def test_study_next_none_when_no_cards():
    assert dd.study_next(_rows(), dd.load_taxonomy()) is None


def test_study_next_prefers_highest_weight_unstudied_with_cards():
    nxt = dd.study_next(
        _rows(
            **{
                "topic::algebra::linear": FakeRow(total_cards=4, reviewed_count=0),
                "topic::calculus::integral_single": FakeRow(
                    total_cards=5, reviewed_count=0
                ),
            }
        ),
        dd.load_taxonomy(),
    )
    assert nxt["tag"] == "topic::calculus::integral_single"
    assert nxt["label"] == "Single-variable integral calculus"
    assert "haven't started" in nxt["reason"]


def test_study_next_weakest_when_all_studyable_are_studied():
    nxt = dd.study_next(
        _rows(
            **{
                "topic::calculus::integral_single": FakeRow(
                    total_cards=5, reviewed_count=10, mastered_count=9
                ),
                "topic::algebra::linear": FakeRow(
                    total_cards=5, reviewed_count=10, mastered_count=1
                ),
            }
        ),
        dd.load_taxonomy(),
    )
    assert nxt["tag"] == "topic::algebra::linear"
    assert "weakest" in nxt["reason"].lower()


def test_stats_block_sums_leaves_and_counts_exam_answers():
    s = dd.stats_block(
        _rows(
            **{
                "topic::calculus::integral_single": FakeRow(
                    total_cards=5, reviewed_count=3, mastered_count=2
                ),
                "topic::algebra::linear": FakeRow(
                    total_cards=4, reviewed_count=1, mastered_count=0
                ),
                "topic::calculus": FakeRow(total_cards=5, reviewed_count=3),
                "topic::algebra": FakeRow(total_cards=4, reviewed_count=1),
            }
        ),
        dd.load_taxonomy(),
        [{"correct": True}, {"correct": False}, {"nope": 1}],
    )
    assert s["cards_total"] == 9
    assert s["cards_reviewed"] == 4
    assert s["topics_covered"] == 2
    assert s["topics_total"] == 17
    assert s["exam_questions_answered"] == 2
    by_bucket = {b["bucket"]: b for b in s["by_bucket"]}
    assert by_bucket["calculus"]["reviewed"] == 3
    assert by_bucket["additional"]["reviewed"] == 0


def test_build_view_model_includes_stats_study_next_and_leaf_labels():
    vm = dd.build_view_model(
        _rows(
            **{
                "topic::calculus::integral_single": FakeRow(
                    total_cards=5, reviewed_count=0
                )
            }
        ),
        generated_at="t",
    )
    assert vm["stats"]["cards_total"] == 5
    assert vm["study_next"]["tag"] == "topic::calculus::integral_single"
    labels = {leaf["tag"]: leaf["label"] for leaf in vm["coverage"]["leaves"]}
    assert labels["topic::calculus::integral_single"] == "Single-variable integral calculus"


def test_build_view_model_study_next_none_on_empty_deck():
    vm = dd.build_view_model(_rows(), generated_at="t")
    assert vm["study_next"] is None
    assert vm["stats"]["cards_reviewed"] == 0
