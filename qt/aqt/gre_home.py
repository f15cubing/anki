# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""GRE Home — a friendly landing page (Tools ▸ GRE Home, auto-opens on startup).

A read-only SvelteKit surface (`ts/routes/gre-home`) fetching the existing
`greDashboardData` (three separated scores + study stats + the best topic to study
next) and `greExamCapacity` (Exam-Mode lock state). Imperative actions arrive over the
webview bridge (`pycmd`), handled here on the main thread:

  - ``gre:study``          build/enter a filtered deck for the next-best topic + review
  - ``gre:dashboard``      open the full readiness dashboard
  - ``gre:exam``           open Exam Mode
  - ``gre:method``         open the "How this differs from FSRS" page
  - ``gre:startup:on|off`` toggle the startup auto-open flag

Honesty ceilings are inherited from the dashboard view-model (three scores stay
separate; Readiness never a bare number). The only writes are the standard, undoable
filtered-deck op (study-next) and one non-undoable ``col.conf`` flag (startup toggle).
"""

from __future__ import annotations

import sys
from typing import Any

import aqt
import aqt.main
from anki.decks import DeckId
from aqt import gui_hooks
from aqt.qt import (
    QAction,
    QDialog,
    Qt,
    QTimer,
    QVBoxLayout,
    qconnect,
)
from aqt.utils import (
    add_close_shortcut,
    disable_help_button,
    restoreGeom,
    saveGeom,
    tooltip,
)
from aqt.webview import AnkiWebView, AnkiWebViewKind

_SHOW_ON_STARTUP_KEY = "gre_home_show_on_startup"
_STUDY_NEXT_DECK_NAME = "GRE · Study next"

# Single live dialog: reopening focuses it rather than stacking windows (matters
# because it also auto-opens on startup).
_active: GreHome | None = None
_startup_registered = False


class GreHome(QDialog):
    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        mw.garbage_collect_on_dialog_finish(self)
        self.mw = mw
        self.name = "greHome"
        disable_help_button(self)
        self.web = AnkiWebView(kind=AnkiWebViewKind.GRE_HOME)
        self.web.set_bridge_command(self._on_bridge_cmd, self)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self.setLayout(layout)
        self.setMinimumSize(820, 640)
        restoreGeom(self, self.name, default_size=(960, 760))
        add_close_shortcut(self)
        self.web.load_sveltekit_page("gre-home")
        self.show()
        self.activateWindow()

    # -- bridge ---------------------------------------------------------------

    def _on_bridge_cmd(self, cmd: str) -> Any:
        if cmd == "gre:study":
            self._study_next()
        elif cmd == "gre:dashboard":
            from aqt.gre_dashboard import show_gre_dashboard

            show_gre_dashboard(self.mw)
        elif cmd == "gre:exam":
            from aqt.gre_exam import show_gre_exam

            show_gre_exam(self.mw)
        elif cmd == "gre:method":
            from aqt.gre_method import show_gre_method

            show_gre_method(self.mw)
        elif cmd in ("gre:startup:on", "gre:startup:off"):
            self._set_startup(cmd.endswith(":on"))
        return None

    def _set_startup(self, on: bool) -> None:
        try:
            # A UI preference, not a study action: no undo entry, history preserved.
            self.mw.col.set_config(_SHOW_ON_STARTUP_KEY, bool(on), undoable=False)
            tooltip(
                "Home will open on startup."
                if on
                else "Home won't open on startup.",
                parent=self,
            )
        except Exception as exc:  # pragma: no cover - defensive UI guard
            print(f"GRE home startup toggle failed: {exc}", file=sys.stderr)

    # -- study next -----------------------------------------------------------

    def _study_next(self) -> None:
        """Recompute the best studyable topic server-side and drop into its review."""
        col = getattr(self.mw, "col", None)
        if col is None:
            return
        try:
            from aqt.gre import dashboard_data as dd

            rows = {r.topic: r for r in col.mastery_query(dd.query_topics())}
            nxt = dd.study_next(rows, dd.load_taxonomy())
        except Exception as exc:  # pragma: no cover - defensive UI guard
            print(f"GRE study-next compute failed: {exc}", file=sys.stderr)
            tooltip("Couldn't pick a topic to study.", parent=self)
            return
        if not nxt:
            tooltip("No GRE cards to study yet — import the deck first.", parent=self)
            return
        self._launch_filtered_study(nxt["tag"], nxt.get("label") or nxt["tag"])

    def _launch_filtered_study(self, tag: str, label: str) -> None:
        from aqt.gre import dashboard_data as dd
        from aqt.operations.scheduling import add_or_update_filtered_deck

        mw = self.mw
        col = mw.col
        # Never trust a search string from the client: only our own leaf tags reach it.
        if tag not in set(dd.all_leaf_tags()):
            tooltip("Unknown topic.", parent=self)
            return

        existing = col.decks.id_for_name(_STUDY_NEXT_DECK_NAME)
        try:
            deck = col.sched.get_or_create_filtered_deck(deck_id=existing or DeckId(0))
        except Exception:
            deck = col.sched.get_or_create_filtered_deck(deck_id=DeckId(0))
        deck.name = _STUDY_NEXT_DECK_NAME
        term = deck.config.search_terms[0]
        term.search = f"tag:{tag} -is:suspended"
        term.limit = 80

        def on_success(out: Any) -> None:
            try:
                col.decks.select(out.id)
                col.startTimebox()
            except Exception as exc:  # pragma: no cover - defensive UI guard
                print(f"GRE study-next select failed: {exc}", file=sys.stderr)
            self._close_self()
            # Defer past the op's own redraw (success runs BEFORE operation_did_execute),
            # then enter review of the just-built topic deck (Anki lands on the deck's
            # overview if nothing is due).
            QTimer.singleShot(0, lambda: mw.moveToState("review"))

        add_or_update_filtered_deck(parent=mw, deck=deck).success(
            on_success
        ).run_in_background()

    def _close_self(self) -> None:
        try:
            self.close()
        except Exception:  # pragma: no cover - defensive UI guard
            pass

    def reject(self) -> None:
        global _active
        self.web.cleanup()
        self.web = None  # type: ignore
        saveGeom(self, self.name)
        if _active is self:
            _active = None
        QDialog.reject(self)


def show_gre_home(mw: aqt.main.AnkiQt) -> None:
    global _active
    if _active is not None:
        try:
            _active.activateWindow()
            _active.raise_()
            return
        except Exception:
            _active = None
    _active = GreHome(mw)


def handle_gre_home(mw: aqt.main.AnkiQt, caller: QDialog | None = None) -> None:
    """Focus/open GRE Home, closing the calling dialog if it isn't Home itself.

    The shared target of the ``gre:home`` webview bridge command fired by the
    "← Home" link on the other GRE surfaces (dashboard / exam / method); wired via
    ``aqt.gre.nav.install_gre_home_bridge``. Reuses the Home singleton
    (``show_gre_home``); the caller — a QDialog that is never the live Home — is
    closed so we don't leave a stack of windows behind.

    The close is **deferred** (``QTimer.singleShot(0, …)``): this runs inside the
    caller webview's own bridge callback, so tearing that webview down synchronously
    here would free it mid-call.
    """
    show_gre_home(mw)
    if caller is not None and caller is not _active:
        QTimer.singleShot(0, caller.close)


def _maybe_open_on_startup() -> None:
    mw = aqt.mw
    if mw is None or getattr(mw, "col", None) is None:
        return
    try:
        if not mw.col.get_config(_SHOW_ON_STARTUP_KEY, True):
            return
    except Exception:
        return
    # Defer so the deck browser paints first; re-check the collection at fire time.
    QTimer.singleShot(250, lambda: _safe_open(mw))


def _safe_open(mw: aqt.main.AnkiQt) -> None:
    if getattr(mw, "col", None) is None:
        return
    try:
        show_gre_home(mw)
    except Exception as exc:  # pragma: no cover - defensive UI guard
        print(f"GRE home auto-open failed: {exc}", file=sys.stderr)


def setup_gre_home_menu(mw: aqt.main.AnkiQt) -> None:
    action = QAction("GRE Home", mw)
    qconnect(action.triggered, lambda: show_gre_home(mw))
    mw.form.menuTools.addAction(action)

    global _startup_registered
    if not _startup_registered:
        gui_hooks.profile_did_open.append(_maybe_open_on_startup)
        _startup_registered = True
    # If the profile is already open (hook registered after profile_did_open fired),
    # run the startup check once now.
    if getattr(mw, "col", None) is not None:
        _maybe_open_on_startup()
