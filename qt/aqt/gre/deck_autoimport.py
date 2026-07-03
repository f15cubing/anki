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

History preservation relies on stable note GUIDs. The pipeline now derives GUIDs
from a rendering-independent uid, so uid->uid re-imports update cards in place. A
deck bundled under the OLD content-hash scheme can't be matched by GUID, so a
one-time cleanup (`gre_deck_guid_scheme` gate) removes those legacy notes before
the first uid import to avoid duplicating the whole deck.

KNOWN LIMITATION (note-type template refresh on EXISTING installs): a bumped
``GRE_DECK_VERSION`` re-triggers this import, and a FRESH install always gets the
current bundled template. But because our ``.apkg`` build is byte-deterministic
(fixed note-type ``mod``), ``update_notetypes=IF_NEWER`` sees the incoming
note-type as "not newer" and keeps the existing template body — so a pure card-
*template* change (e.g. the interactive MCQ template) does NOT reach installs that
already imported an earlier bundle. ``ALWAYS`` was also verified not to force it
(same-id merge keeps existing templates). Refreshing the template on existing
installs is a separate follow-up (version-derived note-type ``mod``, or a template
migration); it is out of scope for a content re-bundle.
"""

from __future__ import annotations

import os

from anki.collection import Collection, ImportAnkiPackageOptions, ImportAnkiPackageRequest
from anki.import_export_pb2 import ImportAnkiPackageUpdateCondition

GRE_DECK_VERSION = "2026-07-03b"

_ASSET = os.path.join(os.path.dirname(__file__), "data", "gre-study-deck.apkg")
_CONFIG_KEY = "gre_deck_version"

# Note GUIDs are derived from a stable, rendering-independent uid (pipeline
# `build_deck`). Decks bundled BEFORE that scheme used content-hash GUIDs, which
# the current package can't match by GUID -> a plain re-import would duplicate the
# whole deck. We stamp the scheme we imported under this key; on a mismatch we run
# a one-time cleanup (below) before importing.
_GUID_SCHEME_KEY = "gre_deck_guid_scheme"
_GUID_SCHEME = "uid"

# The two note types the bundled deck ships (see pipeline/build_deck.py). Used to
# identify previously-bundled notes for the one-time pre-uid cleanup.
_BUNDLED_NOTETYPES = (
    "GRE Math Basic (leaf-tagged)",
    "GRE Math MCQ (leaf-tagged)",
)

_IF_NEWER = (
    ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER
)


def _remove_pre_uid_bundled_notes(col: Collection) -> None:
    """One-time migration off the legacy content-hash GUID scheme.

    When the stored scheme isn't the current uid scheme, the previously-bundled
    notes have content-hash GUIDs the new package can't match -> a plain import
    would duplicate the deck. Remove those notes (identified by our two bundled
    note types) exactly once; the subsequent import lays down uid-GUID cards, and
    every future uid->uid import matches by GUID and preserves the user's history.

    A fresh install has no such notes, so this is a harmless no-op there.
    """
    nids: list = []
    for name in _BUNDLED_NOTETYPES:
        nids.extend(col.find_notes('note:"{}"'.format(name)))
    if nids:
        col.remove_notes(nids)


def _import_bundled(col: Collection) -> int:
    """Import the bundled deck and stamp the version + GUID-scheme config keys.

    Returns the number of net-new cards added (0 on a content-only uid->uid
    update where all GUIDs already existed).
    """
    if col.get_config(_GUID_SCHEME_KEY, None) != _GUID_SCHEME:
        _remove_pre_uid_bundled_notes(col)
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
    col.set_config(_GUID_SCHEME_KEY, _GUID_SCHEME)
    return col.card_count() - before


def _is_up_to_date(col: Collection) -> bool:
    """True only when BOTH the version and the GUID scheme are current.

    Gating on the scheme too (not just the version) means an install that already
    re-imported under a buggy older build — same version, but a stale/absent GUID
    scheme, and therefore possibly duplicated — still gets repaired on next launch.
    """
    return (
        col.get_config(_CONFIG_KEY, None) == GRE_DECK_VERSION
        and col.get_config(_GUID_SCHEME_KEY, None) == _GUID_SCHEME
    )


def _run_if_needed(col: Collection) -> bool:
    """Import only when the deck is not up-to-date (version or GUID scheme stale).

    Returns True if an import was performed, False if already up-to-date.
    """
    if _is_up_to_date(col):
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
    if _is_up_to_date(col):
        return

    # QueryOp (not CollectionOp) is intentional: this one-time setup import is not
    # a user-undoable action, so we deliberately keep it off the undo stack. Do not
    # "fix" this to CollectionOp. The op calls _run_if_needed (not _import_bundled)
    # so it re-checks the version inside the background thread — self-contained and
    # safe against a redundant dispatch.
    from aqt.operations import QueryOp

    QueryOp(
        parent=mw,  # type: ignore[arg-type]
        op=lambda col: _run_if_needed(col),
        success=lambda _ran: mw.reset(),  # type: ignore[union-attr]
    ).run_in_background()
