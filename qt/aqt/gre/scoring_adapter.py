# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Desktop-authoritative scoring adapter (Task 6).

Gathers live inputs (the W1 mastery query -> coverage + the Memory range via the
W2 dashboard view-model), calls the pure-stdlib ``scoring/`` package, assembles
the three-score ``gre_scorecard`` payload, and writes it to ``col.conf`` so it
rides W4 collection sync to AnkiDroid (rendered read-only there).

Honesty ceilings (PRD D2 / AGENTS.md):
- The three scores stay **separate**; never blended.
- Readiness is a RANGE gated by the give-up rule, **never a bare number**. On
  desktop there is no exam/MCQ attempt bank yet, so P(correct) cannot be
  modelled; Readiness therefore stays gated OFF with its reasons + evidence
  panel. We deliberately do NOT derive Readiness from Memory recall -- that would
  violate the firewall / no-blend ceiling.
- Read-only w.r.t. study data: the only mutation is the ``gre_scorecard`` config
  value (the synced transport), written undoable=False so undo history is kept.
"""

from __future__ import annotations

import datetime
import os
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from anki.collection import Collection

# Make the repo-root ``scoring/`` package importable from inside the anki
# submodule (anki/qt/aqt/gre/ -> repo root is four levels up).
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_CONFIG_KEY = "gre_scorecard"
_SOURCE = (
    "desktop; Memory from FSRS mastery; Performance/Readiness await the exam "
    "attempt bank (validity unestablished at n\u22480)"
)


def compute_and_write_scorecard(col: Collection) -> dict[str, Any]:
    """Compute the three-score card from live collection state and persist it.

    Returns the payload written to ``col.conf["gre_scorecard"]``.
    """
    from scoring import readiness as rd  # type: ignore[import-not-found]
    from scoring import scorecard as sc  # type: ignore[import-not-found]

    from aqt.gre import dashboard_data as dd

    tax = dd.load_taxonomy()
    topics = dd.query_topics(tax)
    rows = col.mastery_query(topics)
    rows_by_tag = {r.topic: r for r in rows}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    vm = dd.build_view_model(rows_by_tag, generated_at=now)

    coverage = vm["coverage"]["studied_pct"]
    total_reviewed = sum(
        rows_by_tag[dd.bucket_tag(b.name, tax)].reviewed_count for b in tax.buckets
    )

    # Memory: the dashboard's ETS-weighted headline range (None until any review).
    headline = vm["memory"]["headline"]
    if headline is not None:
        memory = {
            "estimate": headline["point"],
            "low": headline["low"],
            "high": headline["high"],
            "coverage_pct": coverage,
        }
    else:
        memory = {
            "estimate": None,
            "low": None,
            "high": None,
            "coverage_pct": coverage,
        }

    # Performance: no desktop attempt bank yet (arrives with the MCQ surface).
    performance = {
        "estimate": None,
        "low": None,
        "high": None,
        "state": "not_available",
    }

    # Readiness: gated. Without an attempt bank we cannot model P(correct), so we
    # do not project a score (and never derive it from Memory). Report the
    # give-up reasons (review/coverage proxies) plus the missing-attempts reason.
    reasons = rd.give_up(total_reviewed, coverage, width=0.0)
    reasons.append("no exam attempts yet")
    readiness = {
        "shown": False,
        "estimate": None,
        "low": None,
        "high": None,
        "width": None,
        "reasons": reasons,
        "coverage_pct": coverage,
        "confidence": "low",
        "best_next_topic": vm["readiness"]["next_best_topic"],
    }

    card = sc.build(
        memory=memory,
        performance=performance,
        readiness=readiness,
        source=_SOURCE,
        updated_at=now,
    )
    col.set_config(_CONFIG_KEY, card)
    return card
