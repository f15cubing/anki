# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Data for the interactive interleaving demo on the "how this differs from FSRS" page.

Pure + read-only (no `aqt.mw`, no collection, no Qt): mirrors `dashboard_data.py` /
`exam.py`. It runs the **vendored** FSRS-cooperative interleaving algorithm
(`interleave.py`) on a small, deterministic example due queue so the explainer page can
show blocked vs. interleaved ordering with the real algorithm's own metrics — not a
JS re-implementation and not the live study queue.
"""

from __future__ import annotations

from aqt.gre import interleave

# A small example due queue in FSRS priority order (index 0 = most urgent), deliberately
# "blocked" (runs of one type) so interleaving visibly disperses it. Authentic GRE
# taxonomy leaves; by default each leaf is its own confusable cluster (the interleave.py
# default), so dispersion alternates confusable problem types (e.g. differentiate vs
# integrate — exactly the "pick the strategy first" demand a GRE item makes).
_LEAVES: list[tuple[str, str]] = [
    ("topic::calculus::differential_single", "Differentiate"),
    ("topic::calculus::integral_single", "Integrate"),
    ("topic::algebra::linear", "Linear algebra"),
    ("topic::additional::real_analysis", "Real analysis"),
]

LEAF_LABEL: dict[str, str] = {leaf: label for leaf, label in _LEAVES}

# Bounds so a hand-crafted request can only ever reorder the example (never anything
# pathological) — the endpoint stays pure regardless of input.
K_MIN, K_MAX = 0, 5
W_MIN, W_MAX = 1, 12


def _example_queue() -> list[tuple[str, str]]:
    queue: list[tuple[str, str]] = []
    n = 0
    for leaf, _label in _LEAVES:
        for _ in range(3):  # three of each type, blocked: AAABBBCCCDDD
            n += 1
            queue.append((f"c{n:02d}", leaf))
    return queue


EXAMPLE_QUEUE: list[tuple[str, str]] = _example_queue()


def _clamp(value: object, lo: int, hi: int, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return default
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, ivalue))


def _chips(order: list[tuple[str, str]]) -> list[dict]:
    return [
        {
            "id": cid,
            "leaf": leaf,
            "label": LEAF_LABEL.get(leaf, leaf),
            "cluster": interleave.cluster_of(leaf),
        }
        for cid, leaf in order
    ]


def build_interleave_demo(
    k: object = interleave.DEFAULT_K, w: object = interleave.DEFAULT_W
) -> dict:
    """Run the real vendored algorithm on ``EXAMPLE_QUEUE``; return orders + metrics.

    Pure + read-only. ``k`` (avoid the last ``k`` clusters) and ``w`` (displacement
    bound) are clamped to sane ranges. Returns a JSON-serializable dict with the blocked
    (FSRS) order, the interleaved order, and the spec's two metrics.
    """
    kk = _clamp(k, K_MIN, K_MAX, interleave.DEFAULT_K)
    ww = _clamp(w, W_MIN, W_MAX, interleave.DEFAULT_W)
    blocked = interleave.blocked_order(EXAMPLE_QUEUE)
    result = interleave.interleave(EXAMPLE_QUEUE, k=kk, w=ww)
    return {
        "k": kk,
        "w": ww,
        "k_range": [K_MIN, K_MAX],
        "w_range": [W_MIN, W_MAX],
        "blocked": _chips(blocked),
        "interleaved": _chips(result.order),
        "metrics": {
            "blocked_dispersion": result.blocked_dispersion,
            "adjacency_dispersion": result.adjacency_dispersion,
            "displacement_mean": result.displacement_mean,
            "displacement_max": result.displacement_max,
            "used_fallback": result.used_fallback,
        },
        # distinct clusters in queue order → a stable colour legend for the client
        "clusters": [{"cluster": leaf, "label": label} for leaf, label in _LEAVES],
    }
