# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pytest

from aqt.gre import exam


def _item(id, bucket, correct_index=0):
    return {
        "id": id,
        "leaf_tag": f"topic::{bucket}::leaf",
        "options": ["a", "b", "c", "d", "e"],
        "correct_index": correct_index,
        "difficulty": 2,
    }


def _bank(calc=40, alg=20, add=20):
    return (
        [_item(f"calculus-{i:03d}", "calculus") for i in range(calc)]
        + [_item(f"algebra-{i:03d}", "algebra") for i in range(alg)]
        + [_item(f"additional-{i:03d}", "additional") for i in range(add)]
    )


# --- pace + blueprint ---


def test_official_pace_and_presets():
    assert exam.PRESETS == {"full": 66, "half": 33, "third": 22, "mini": 11}
    assert exam.preset_seconds(66) == 170 * 60  # full length = 2h50m exactly
    per_item = {n: exam.preset_seconds(n) / n for n in exam.PRESETS.values()}
    assert max(per_item.values()) - min(per_item.values()) < 1e-9


def test_bucket_of():
    assert exam.bucket_of("topic::calculus::integral_single") == "calculus"
    with pytest.raises(ValueError):
        exam.bucket_of("calculus")


def test_blueprint_counts_sum_and_favor_calculus():
    for size in exam.PRESETS.values():
        counts = exam.blueprint_counts(size)
        assert sum(counts.values()) == size
        assert counts["calculus"] >= counts["algebra"]
        assert counts["calculus"] >= counts["additional"]
    assert exam.blueprint_counts(66)["calculus"] == 33


# --- assembly ---


def test_assemble_is_blueprint_matched_and_distinct():
    form = exam.assemble_form(_bank(), 11, seed=42)
    assert len(form) == 11
    assert len({it["id"] for it in form}) == 11
    counts = {}
    for it in form:
        b = exam.bucket_of(it["leaf_tag"])
        counts[b] = counts.get(b, 0) + 1
    assert counts == exam.blueprint_counts(11)


def test_assemble_is_deterministic_for_a_seed():
    a = [it["id"] for it in exam.assemble_form(_bank(), 22, seed=7)]
    b = [it["id"] for it in exam.assemble_form(_bank(), 22, seed=7)]
    assert a == b
    assert a != [it["id"] for it in exam.assemble_form(_bank(), 22, seed=8)]


def test_insufficient_items_raises():
    with pytest.raises(exam.InsufficientItemsError):
        exam.assemble_form([_item(f"c{i}", "calculus") for i in range(3)], 11, seed=1)


# --- vendored items + firewall ---


def test_vendored_items_load_and_assemble_firewalled():
    items = exam.load_exam_items()
    assert len(items) >= 11
    form = exam.assemble_form(items, exam.PRESETS["mini"], seed=42)
    assert len(form) == exam.PRESETS["mini"]
    # form-level firewall: only authored eval-bank items ever reach a mock
    assert all(str(it["id"]).startswith("eval-") for it in form)


# --- capacity / feasibility (fixes the Exam Mode "API error") ---


def test_bucket_pool_sizes_counts_by_bucket():
    pools = exam.bucket_pool_sizes(_bank(calc=8, alg=7, add=9))
    assert pools == {"calculus": 8, "algebra": 7, "additional": 9}


def test_size_is_feasible_respects_pools():
    small = _bank(calc=8, alg=7, add=9)  # mirrors the vendored p0 pool
    assert exam.size_is_feasible(small, 11) is True  # mini fits
    assert exam.size_is_feasible(small, 66) is False  # full does not
    assert exam.size_is_feasible(small, 0) is False
    big = _bank(calc=40, alg=20, add=20)
    assert all(exam.size_is_feasible(big, n) for n in exam.PRESETS.values())


def test_max_feasible_size_is_the_boundary():
    small = _bank(calc=8, alg=7, add=9)
    m = exam.max_feasible_size(small)
    assert exam.size_is_feasible(small, m)
    assert not exam.size_is_feasible(small, m + 1)
    assert m >= exam.PRESETS["mini"]  # a mini mock is buildable
    assert m < exam.PRESETS["third"]  # but not a 22-item one


def test_feasible_presets_shape_and_flags():
    presets = exam.feasible_presets(_bank(calc=8, alg=7, add=9))
    by_id = {p["id"]: p for p in presets}
    assert set(by_id) == set(exam.PRESETS)
    for p in presets:
        assert set(p) == {"id", "items", "seconds", "feasible"}
        assert p["items"] == exam.PRESETS[p["id"]]
        assert p["seconds"] == exam.preset_seconds(p["items"])
    assert by_id["mini"]["feasible"] is True
    assert by_id["full"]["feasible"] is False


def test_vendored_p0_supports_full_length_mock():
    # The vendored held-out (p0) bank was enlarged with deterministic,
    # firewall-safe demo items (`eval-p0-gen-*`, gen: generated) so Exam Mode can
    # build the official full-length form under the 50/25/25 blueprint. Every
    # named preset must therefore report feasible up front.
    items = exam.load_exam_items(partition="p0")
    flags = {p["id"]: p["feasible"] for p in exam.feasible_presets(items)}
    assert flags["mini"] is True
    assert flags["third"] is True
    assert flags["half"] is True
    assert flags["full"] is True
    assert exam.max_feasible_size(items) >= exam.PRESETS["full"]
    # ...and a full 66-item form actually assembles, drawn only from the bank.
    form = exam.assemble_form(items, exam.PRESETS["full"], seed=1)
    assert len(form) == exam.PRESETS["full"]
    assert all(str(it["id"]).startswith("eval-") for it in form)


# --- scoring ---

FORM = [
    _item("c1", "calculus", 0),
    _item("c2", "calculus", 1),
    _item("a1", "algebra", 2),
    _item("x1", "additional", 3),
]


def test_rights_only_no_penalty_for_wrong_or_omitted():
    s = exam.score_form(
        FORM, {"c1": 0, "c2": 0, "a1": 2}
    )  # c1,a1 right; c2 wrong; x1 omitted
    assert (s["correct"], s["total"], s["answered"], s["omitted"]) == (2, 4, 3, 1)


def test_all_correct_and_empty():
    assert exam.score_form(FORM, {"c1": 0, "c2": 1, "a1": 2, "x1": 3})["correct"] == 4
    empty = exam.score_form(FORM, {})
    assert empty["correct"] == 0 and empty["proportion"]["point"] == 0.0


def test_per_bucket_breakdown():
    s = exam.score_form(FORM, {"c1": 0, "c2": 0, "a1": 2, "x1": 3})
    assert s["by_bucket"]["calculus"] == {"correct": 1, "total": 2}
    assert s["by_bucket"]["algebra"] == {"correct": 1, "total": 1}


def test_wilson_bounds():
    p, lo, hi = exam.wilson_interval(8, 10)
    assert p == 0.8 and 0.0 <= lo < p < hi <= 1.0
    assert exam.wilson_interval(0, 0) == (0.0, 0.0, 0.0)


def test_attempts_record_shape():
    rec = {
        r["item_id"]: r
        for r in exam.attempts_record(FORM, {"c1": 0, "c2": 0}, {"c1": 42.5})
    }
    assert rec["c1"]["correct"] is True and rec["c1"]["latency_s"] == 42.5
    assert rec["c2"]["correct"] is False and rec["x1"]["chosen"] is None


# --- 70% studied-coverage lock (Home + Exam Mode) ---------------------------


def test_coverage_meets_threshold_at_and_below_boundary():
    assert exam.coverage_meets_threshold(7, 10) is True  # exactly 0.70
    assert exam.coverage_meets_threshold(6, 10) is False  # 0.60
    assert exam.coverage_meets_threshold(12, 17) is True  # 0.706 (>=12 of 17)
    assert exam.coverage_meets_threshold(11, 17) is False  # 0.647
    assert exam.coverage_meets_threshold(0, 0) is False  # no topics -> never


def test_coverage_lock_reason_reports_progress_and_remaining():
    # ceil(0.70 * 17) = 12 topics needed; studied 3 -> 9 more.
    msg = exam.coverage_lock_reason(3, 17)
    assert "70%" in msg
    assert "3" in msg  # studied count
    assert "9 more" in msg


def test_coverage_lock_reason_singular_when_one_remaining():
    # 11/17 studied (64%), needs 12 -> exactly 1 more.
    assert "1 more topic" in exam.coverage_lock_reason(11, 17)
    assert "1 more topics" not in exam.coverage_lock_reason(11, 17)
