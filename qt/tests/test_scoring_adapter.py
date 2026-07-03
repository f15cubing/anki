# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Desktop scoring adapter (Task 6): gather live inputs, call the pure `scoring/`
package, and write the synced `gre_scorecard` col.conf value that AnkiDroid
renders read-only. No Qt required for these tests."""

from anki.collection import Collection
from aqt.gre.scoring_adapter import compute_and_write_scorecard

_SCORECARD_KEYS = {
    "version",
    "updated_at",
    "source",
    "memory",
    "performance",
    "readiness",
}


def _fresh(tmp_path) -> Collection:
    return Collection(str(tmp_path / "col.anki2"))


def test_writes_gated_scorecard_on_fresh_collection(tmp_path):
    col = _fresh(tmp_path)
    try:
        sc = compute_and_write_scorecard(col)
        # Three scores kept separate; full schema present (never blended).
        assert set(sc) == _SCORECARD_KEYS
        # Persisted to the synced col.conf transport (rides W4 sync to the phone).
        assert col.get_config("gre_scorecard") == sc
        # Fresh collection: far under 200 reviews -> Readiness gated OFF, never a bare number.
        assert sc["readiness"]["shown"] is False
        assert sc["readiness"]["estimate"] is None
        assert "<200 graded reviews" in sc["readiness"]["reasons"]
    finally:
        col.close()


def test_gated_readiness_carries_full_evidence_panel(tmp_path):
    # Ceiling: never show Readiness without the evidence panel, even when gated off.
    col = _fresh(tmp_path)
    try:
        sc = compute_and_write_scorecard(col)
        r = sc["readiness"]
        assert {"coverage_pct", "confidence", "reasons", "best_next_topic"} <= set(r)
        assert r["reasons"], "gated Readiness must state its reasons"
    finally:
        col.close()


def test_dashboard_open_hook_persists_scorecard(tmp_path):
    # The dashboard's on-open hook computes + writes the synced scorecard.
    # (Imported lazily: the Qt dialog module pulls in aqt.qt.)
    from aqt import gre_dashboard

    class _FakeMw:
        def __init__(self, col):
            self.col = col

    col = _fresh(tmp_path)
    try:
        gre_dashboard._write_scorecard(_FakeMw(col))
        card = col.get_config("gre_scorecard")
        assert card["version"] == 1
        assert card["readiness"]["shown"] is False
    finally:
        col.close()
