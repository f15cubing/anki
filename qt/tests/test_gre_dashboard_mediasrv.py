# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import json
import types

import aqt.mediasrv as m
from aqt.gre import dashboard_data as dd


def test_page_and_endpoint_are_registered():
    assert m.is_sveltekit_page("gre-dashboard")
    assert "greDashboardData" in m.post_handlers


def test_endpoint_returns_view_model_and_is_read_only(monkeypatch):
    from dataclasses import dataclass

    @dataclass
    class Row:
        topic: str
        total_cards: int = 0
        reviewed_count: int = 0
        mastered_count: int = 0
        avg_recall: float = 0.0

    calls = {"mastery": 0}

    class FakeCol:
        def mastery_query(self, topics):
            calls["mastery"] += 1
            return [Row(topic=t, total_cards=1) for t in topics]

        # Fail loudly if the endpoint tries to mutate.
        def transact(self, *a, **k):  # pragma: no cover
            raise AssertionError("read endpoint must not mutate")

    monkeypatch.setattr(m, "aqt", types.SimpleNamespace(mw=types.SimpleNamespace(col=FakeCol())))
    out = m.gre_dashboard_data()
    vm = json.loads(out.decode("utf-8"))
    assert calls["mastery"] == 1
    assert set(vm.keys()) == {"generated_at", "memory", "coverage", "readiness", "performance"}
    assert len(vm["coverage"]["leaves"]) == 17
