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

TEMPLATE REFRESH on EXISTING installs: the apkg importer keeps an existing
note-type's *template body* on re-import (same-id merge — verified for both
``IF_NEWER`` and ``ALWAYS``; our build is byte-deterministic with a fixed note-type
``mod``, so "is it newer?" is always false). A pure card-*template* change (e.g. the
graded / wrong-answer-locked MCQ template) would therefore never reach installs that
imported an earlier bundle. We fix that independently of the deck version:
``_refresh_bundled_notetype_templates`` reads the canonical ``qfmt``/``afmt``/``css``
straight from the bundled ``.apkg`` (the single source, built from
``pipeline/build_deck.py``) and writes them onto the live note types via
``models.update_dict`` — a text-only update that touches no fields, ids, notes, or
scheduling, so review history is preserved. It runs once per ``_TEMPLATE_REVISION``
(a separate ``col.conf`` gate), so shipping a new template does not require
re-importing the whole deck. A fresh install already has the current template, so the
refresh is a harmless no-op there.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import zipfile

from anki.collection import (
    Collection,
    ImportAnkiPackageOptions,
    ImportAnkiPackageRequest,
)
from anki.import_export_pb2 import ImportAnkiPackageUpdateCondition

GRE_DECK_VERSION = "2026-07-03b"

# Bumped whenever the bundled note-type *templates* change without a deck-content
# re-import (a pure qfmt/afmt/css edit). Gates the one-time in-place template refresh
# below so existing installs pick up the new template on next launch.
_TEMPLATE_REVISION = "2026-07-05a-mcq-graded-lockdown"
_TEMPLATE_REVISION_KEY = "gre_deck_template_revision"

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
    col.import_anki_package(ImportAnkiPackageRequest(package_path=_ASSET, options=opts))
    col.set_config(_CONFIG_KEY, GRE_DECK_VERSION)
    col.set_config(_GUID_SCHEME_KEY, _GUID_SCHEME)
    return col.card_count() - before


def _bundled_models_json() -> dict | None:
    """Read the note-type ``models`` JSON out of the bundled ``.apkg`` (or None).

    The bundled deck is a legacy-schema package (``collection.anki2``/``.anki21``)
    whose note types live in the ``col.models`` JSON blob. We copy that blob out of
    the zip into a temp DB and read it read-only; any failure returns ``None`` so the
    refresh degrades to a no-op rather than disrupting profile load.
    """
    try:
        with zipfile.ZipFile(_ASSET) as zf:
            names = set(zf.namelist())
            db_name = next(
                (n for n in ("collection.anki2", "collection.anki21") if n in names),
                None,
            )
            if db_name is None:
                return None
            raw = zf.read(db_name)
    except (OSError, zipfile.BadZipFile):
        return None

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as fh:
            fh.write(raw)
            tmp = fh.name
        con = sqlite3.connect(tmp)
        try:
            row = con.execute("SELECT models FROM col LIMIT 1").fetchone()
        finally:
            con.close()
    except (OSError, sqlite3.DatabaseError):
        return None
    finally:
        if tmp is not None:
            try:
                os.remove(tmp)
            except OSError:
                pass

    if not row or not row[0]:
        return None
    try:
        return json.loads(row[0])
    except (ValueError, TypeError):
        return None


def _refresh_bundled_notetype_templates(col: Collection) -> None:
    """Overwrite the bundled note types' card templates + CSS in place.

    Reads the canonical ``qfmt``/``afmt``/``css`` from the bundled ``.apkg`` and
    applies them to the live note types (matched by name, templates matched by
    ``ord``) via ``models.update_dict``. This is a *text-only* update: no fields,
    ids, notes, or scheduling change, so the user's review history is untouched. Only
    writes a note type that actually differs, so it's a no-op on a fresh install (or a
    second run).
    """
    models_json = _bundled_models_json()
    if not models_json:
        return
    by_name = {m.get("name"): m for m in models_json.values() if isinstance(m, dict)}
    for name in _BUNDLED_NOTETYPES:
        src = by_name.get(name)
        if not src:
            continue
        nt = col.models.by_name(name)
        if not nt:
            continue
        changed = False
        css = src.get("css")
        if css is not None and nt.get("css") != css:
            nt["css"] = css
            changed = True
        src_tmpls = {t.get("ord"): t for t in src.get("tmpls", [])}
        for tmpl in nt.get("tmpls", []):
            s = src_tmpls.get(tmpl.get("ord"))
            if not s:
                continue
            for key in ("qfmt", "afmt"):
                new = s.get(key)
                if new is not None and tmpl.get(key) != new:
                    tmpl[key] = new
                    changed = True
        if changed:
            col.models.update_dict(nt)


def _templates_up_to_date(col: Collection) -> bool:
    """True when the bundled-template revision has already been applied."""
    return col.get_config(_TEMPLATE_REVISION_KEY, None) == _TEMPLATE_REVISION


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
    """Bring the bundled deck up to date: import stale content, refresh stale templates.

    Two independent gates: a stale version/GUID-scheme re-imports the deck content; a
    stale template revision refreshes the note-type templates in place (no re-import
    needed). Returns True if either ran, False if already fully up-to-date.
    """
    ran = False
    if not _is_up_to_date(col):
        _import_bundled(col)
        ran = True
    if not _templates_up_to_date(col):
        _refresh_bundled_notetype_templates(col)
        col.set_config(_TEMPLATE_REVISION_KEY, _TEMPLATE_REVISION)
        ran = True
    return ran


def maybe_import_gre_deck(mw: object) -> None:
    """Entry point called from the ``collection_did_load`` hook.

    Guards against a missing collection (shouldn't happen at that hook,
    but be safe), then runs the version-gated import in a background
    QueryOp so the main thread stays unblocked.
    """
    col = getattr(mw, "col", None)
    if col is None:
        return
    if _is_up_to_date(col) and _templates_up_to_date(col):
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
