# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from __future__ import annotations

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


class GreMethod(QDialog):
    """Explainer: how this app's study method differs from standard FSRS.

    A read-only SvelteKit page (interleaving demo + timed mode + three separated
    scores + honesty rule). Mirrors the GreDashboard / GreExam dialog pattern.
    """

    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        mw.garbage_collect_on_dialog_finish(self)
        self.mw = mw
        self.name = "greMethod"
        disable_help_button(self)
        self.web = AnkiWebView(kind=AnkiWebViewKind.GRE_METHOD)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self.setLayout(layout)
        self.setMinimumSize(900, 700)
        restoreGeom(self, self.name, default_size=(1000, 820))
        add_close_shortcut(self)
        self.web.load_sveltekit_page("gre-method")
        self.show()
        self.activateWindow()

    def reject(self) -> None:
        self.web.cleanup()
        self.web = None  # type: ignore
        saveGeom(self, self.name)
        QDialog.reject(self)


def show_gre_method(mw: aqt.main.AnkiQt) -> None:
    GreMethod(mw)


def setup_gre_method_menu(mw: aqt.main.AnkiQt) -> None:
    action = QAction("How this app differs from FSRS", mw)
    qconnect(action.triggered, lambda: show_gre_method(mw))
    mw.form.menuTools.addAction(action)
