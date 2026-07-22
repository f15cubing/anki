# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Tests for the "how this differs from FSRS" explainer page.

Covers the pure interleaving-demo view-model (the real vendored algorithm on the
example queue), the read-only endpoint, and route/handler registration. The page
itself (webview) is verified by the GUI smoke; here we prove the logic + read-only
contract without a running app.
"""

import json
import types

import aqt.mediasrv as m
from aqt.gre import interleave, method_data


def test_page_and_endpoint_are_registered():
    assert m.is_sveltekit_page("gre-method")
    assert "greMethodInterleave" in m.post_handlers


def test_build_demo_is_a_permutation_of_the_example_queue():
    demo = method_data.build_interleave_demo(k=1, w=3)
    example_ids = sorted(cid for cid, _ in method_data.EXAMPLE_QUEUE)
    for key in ("blocked", "interleaved"):
        ids = sorted(c["id"] for c in demo[key])
        # same multiset — nothing added, dropped, or duplicated
        assert ids == example_ids
    # the blocked row is exactly the FSRS order (identity)
    assert [c["id"] for c in demo["blocked"]] == [
        cid for cid, _ in method_data.EXAMPLE_QUEUE
    ]


def test_interleaving_disperses_and_respects_the_displacement_bound():
    demo = method_data.build_interleave_demo(k=1, w=3)
    mtr = demo["metrics"]
    # the example is deliberately blocked, so interleaving must raise dispersion
    assert mtr["adjacency_dispersion"] >= mtr["blocked_dispersion"]
    assert mtr["adjacency_dispersion"] > 0.5
    # no card drifts more than W slots past its FSRS place (urgent cards can't starve)
    assert mtr["displacement_max"] <= demo["w"]
    assert mtr["used_fallback"] is False


def test_k_and_w_are_clamped_and_never_crash():
    lo = method_data.build_interleave_demo(k=-5, w=-9)
    assert lo["k"] == method_data.K_MIN
    assert lo["w"] == method_data.W_MIN
    hi = method_data.build_interleave_demo(k=999, w=999)
    assert hi["k"] == method_data.K_MAX
    assert hi["w"] == method_data.W_MAX
    # non-integers fall back to the algorithm defaults instead of raising
    bad = method_data.build_interleave_demo(k="x", w=None)
    assert bad["k"] == interleave.DEFAULT_K
    assert bad["w"] == interleave.DEFAULT_W


def test_endpoint_returns_demo_and_never_touches_the_collection(monkeypatch):
    from flask import Flask

    class FakeCol:
        # Fail loudly if the endpoint ever reaches for the collection.
        def transact(self, *a, **k):  # pragma: no cover
            raise AssertionError("method page endpoint must not mutate")

        def mastery_query(self, *a, **k):  # pragma: no cover
            raise AssertionError("method page endpoint must not query the collection")

    monkeypatch.setattr(
        m, "aqt", types.SimpleNamespace(mw=types.SimpleNamespace(col=FakeCol()))
    )
    app = Flask(__name__)
    with app.test_request_context(
        data=json.dumps({"k": 2, "w": 4}), content_type="application/binary"
    ):
        out = m.gre_method_interleave()
    demo = json.loads(out.decode("utf-8"))
    assert demo["k"] == 2 and demo["w"] == 4
    assert {"blocked", "interleaved", "metrics", "clusters"} <= set(demo.keys())
