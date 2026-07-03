# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from __future__ import annotations

import sys

import aqt
import aqt.main
from aqt.qt import (
    QAction,
    QDialog,
    Qt,
    QVBoxLayout,
    qconnect,
)
from aqt.utils import add_close_shortcut, disable_help_button, restoreGeom, saveGeom
from aqt.webview import AnkiWebView, AnkiWebViewKind


def _write_scorecard(mw: aqt.main.AnkiQt) -> None:
    """Compute + persist the synced GRE score card (desktop-authoritative).

    Called on dashboard open so the three-score card in ``col.conf`` is fresh and
    rides collection sync to AnkiDroid. Defensive: never block opening the dialog
    if scoring raises.
    """
    try:
        from aqt.gre.scoring_adapter import compute_and_write_scorecard

        compute_and_write_scorecard(mw.col)
    except Exception as exc:  # pragma: no cover - defensive UI guard
        print(f"GRE scorecard compute failed: {exc}", file=sys.stderr)


class GreDashboard(QDialog):
    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        mw.garbage_collect_on_dialog_finish(self)
        self.mw = mw
        self.name = "greDashboard"
        _write_scorecard(mw)
        disable_help_button(self)
        self.web = AnkiWebView(kind=AnkiWebViewKind.GRE_DASHBOARD)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self.setLayout(layout)
        self.setMinimumSize(900, 700)
        restoreGeom(self, self.name, default_size=(1000, 800))
        add_close_shortcut(self)
        self.web.load_sveltekit_page("gre-dashboard")
        self.show()
        self.activateWindow()

    def reject(self) -> None:
        self.web.cleanup()
        self.web = None  # type: ignore
        saveGeom(self, self.name)
        QDialog.reject(self)


def show_gre_dashboard(mw: aqt.main.AnkiQt) -> None:
    GreDashboard(mw)


def setup_gre_dashboard_menu(mw: aqt.main.AnkiQt) -> None:
    action = QAction("GRE readiness dashboard", mw)
    qconnect(action.triggered, lambda: show_gre_dashboard(mw))
    mw.form.menuTools.addAction(action)
