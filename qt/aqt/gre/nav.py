# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Shared GRE navigation — the "← Home" bridge wiring.

The GRE dashboard / exam / method surfaces each show a small "← Home" affordance
(``ts/routes/gre-dashboard/GreHomeLink.svelte``) that fires the ``gre:home`` webview
bridge command. ``install_gre_home_bridge`` registers a bridge handler on a dialog's
webview that routes that one command back to GRE Home (focusing the singleton and
closing the caller) via ``aqt.gre_home.handle_gre_home``.

Kept deliberately tiny: it recognises only ``gre:home`` and otherwise returns
``None`` (the value the QWebChannel bridge JSON-encodes back to the page). The
QWebChannel bridge itself is always wired by ``webview.py``, so no ``webview.py`` /
``mediasrv.py`` change is needed to receive these commands.
"""

from __future__ import annotations

from typing import Any

import aqt
import aqt.main
from aqt.qt import QDialog
from aqt.webview import AnkiWebView

GRE_HOME_CMD = "gre:home"


def install_gre_home_bridge(
    web: AnkiWebView, mw: aqt.main.AnkiQt, dialog: QDialog
) -> None:
    """Wire the ``gre:home`` bridge command on ``web`` to open GRE Home.

    ``dialog`` is both the bridge context (for lifetime management, per
    ``AnkiWebView.set_bridge_command``) and the caller that gets closed once Home
    is focused.
    """

    def _handle(cmd: str) -> Any:
        if cmd == GRE_HOME_CMD:
            from aqt.gre_home import handle_gre_home

            handle_gre_home(mw, dialog)
        return None

    web.set_bridge_command(_handle, dialog)
