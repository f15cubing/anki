# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Version-gated, first-run auto-importer for the bundled GRE study deck.

On each profile open, ``maybe_import_gre_deck`` checks whether the collection's
stored ``gre_deck_version`` key matches ``GRE_DECK_VERSION``.  If it doesn't
(fresh install, or a new deck version shipped with the app), it imports the
bundled .apkg in a background QueryOp so the UI stays responsive.

Import policy (preserves the user's review history on re-import):
  - merge_notetypes=True        — update note-type schema without duplication
  - update_notes=IF_NEWER       — content updates from the package only
  - update_notetypes=IF_NEWER   — schema updates from the package only
  - with_scheduling=False       — do NOT overwrite FSRS state; user history wins
  - with_deck_configs=False     — keep user's deck settings unchanged
"""

from __future__ import annotations

import os

from anki.collection import Collection, ImportAnkiPackageOptions, ImportAnkiPackageRequest
from anki.import_export_pb2 import ImportAnkiPackageUpdateCondition

GRE_DECK_VERSION = "2026-07-02"

_ASSET = os.path.join(os.path.dirname(__file__), "data", "gre-study-deck.apkg")
_CONFIG_KEY = "gre_deck_version"

_IF_NEWER = (
    ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER
)


def _import_bundled(col: Collection) -> int:
    """Import the bundled deck and set the version config key.

    Returns the number of net-new cards added (may be 0 on a content-only
    update where all GUIDs already existed).
    """
    opts = ImportAnkiPackageOptions(
        merge_notetypes=True,
        update_notes=_IF_NEWER,
        update_notetypes=_IF_NEWER,
        with_scheduling=False,
        with_deck_configs=False,
    )
    before = col.card_count()
    col.import_anki_package(
        ImportAnkiPackageRequest(package_path=_ASSET, options=opts)
    )
    col.set_config(_CONFIG_KEY, GRE_DECK_VERSION)
    return col.card_count() - before


def _run_if_needed(col: Collection) -> bool:
    """Import only when the stored version differs from GRE_DECK_VERSION.

    Returns True if an import was performed, False if already up-to-date.
    """
    if col.get_config(_CONFIG_KEY, None) == GRE_DECK_VERSION:
        return False
    _import_bundled(col)
    return True


def maybe_import_gre_deck(mw: object) -> None:
    """Entry point called from the ``collection_did_load`` hook.

    Guards against a missing collection (shouldn't happen at that hook,
    but be safe), then runs the version-gated import in a background
    QueryOp so the main thread stays unblocked.
    """
    col = getattr(mw, "col", None)
    if col is None:
        return
    if col.get_config(_CONFIG_KEY, None) == GRE_DECK_VERSION:
        return

    from aqt.operations import QueryOp

    QueryOp(
        parent=mw,  # type: ignore[arg-type]
        op=lambda col: _import_bundled(col),
        success=lambda _n: mw.reset(),  # type: ignore[union-attr]
    ).run_in_background()
