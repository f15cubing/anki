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
