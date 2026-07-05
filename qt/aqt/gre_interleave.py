# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Tools-menu toggle for review interleaving (PRD §8, D5).

A checkable action that flips ``col.conf["gre_interleave"]``. Off (default) is the
ablation's *blocked* arm — upstream FSRS order; on is the *interleaved* arm. The
reorder itself lives in :mod:`aqt.gre.interleave_review` and is pure presentation
(no scheduling/undo change). Toggling takes effect from the next card fetched.
"""

from __future__ import annotations

import aqt
import aqt.main
from aqt import gui_hooks
from aqt.gre.interleave_review import CONFIG_KEY, interleave_enabled
from aqt.qt import QAction, qconnect

_ACTION_ATTR = "_gre_interleave_action"


def _set_enabled(mw: aqt.main.AnkiQt, on: bool) -> None:
    if mw.col is None:
        return
    # undoable=False (default) → persists + syncs without adding an undo entry.
    mw.col.set_config(CONFIG_KEY, on)


def setup_gre_interleave_menu(mw: aqt.main.AnkiQt) -> None:
    action = QAction("GRE: Interleave reviews (ablation)", mw)
    action.setCheckable(True)
    action.setToolTip(
        "Reorder review cards so consecutive cards come from different confusable "
        "topics (pre-registered interleaving). Off = blocked FSRS order. Takes "
        "effect from the next card."
    )
    qconnect(action.toggled, lambda on: _set_enabled(mw, on))
    mw.form.menuTools.addAction(action)
    setattr(mw, _ACTION_ATTR, action)

    def _sync_checked(_col: object = None) -> None:
        act = getattr(mw, _ACTION_ATTR, None)
        if act is None:
            return
        on = mw.col is not None and interleave_enabled(mw.col)
        # Reflect persisted state without re-firing `toggled` (which would write).
        act.blockSignals(True)
        act.setChecked(on)
        act.blockSignals(False)

    gui_hooks.collection_did_load.append(lambda _col: _sync_checked())
    _sync_checked()
