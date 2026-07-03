# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Tests for the version-gated GRE deck auto-importer (no Qt required)."""

from anki.collection import Collection
from aqt.gre import deck_autoimport as ai


def _fresh(tmp_path) -> Collection:
    return Collection(str(tmp_path / "col.anki2"))


def test_first_import_adds_deck(tmp_path):
    col = _fresh(tmp_path)
    n = ai._import_bundled(col)
    assert n > 5000, f"Expected >5000 cards added, got {n}"
    assert col.get_config("gre_deck_version") == ai.GRE_DECK_VERSION
    col.close()


def test_reimport_same_version_is_noop(tmp_path):
    col = _fresh(tmp_path)
    ai._run_if_needed(col)
    before = col.card_count()
    ran = ai._run_if_needed(col)
    assert not ran, "Second _run_if_needed at same version should return False"
    assert col.card_count() == before, (
        f"Card count changed on second import: {before} → {col.card_count()}"
    )
    col.close()


def test_run_if_needed_triggers_on_missing_version(tmp_path):
    col = _fresh(tmp_path)
    assert col.get_config("gre_deck_version", None) is None
    ran = ai._run_if_needed(col)
    assert ran, "_run_if_needed should return True when version not set"
    assert col.card_count() > 5000
    col.close()


def test_first_import_stamps_guid_scheme(tmp_path):
    col = _fresh(tmp_path)
    ai._import_bundled(col)
    assert col.get_config(ai._GUID_SCHEME_KEY) == ai._GUID_SCHEME
    col.close()


def test_pre_uid_reimport_does_not_duplicate(tmp_path):
    # Simulate a pre-uid install: the bundled deck is present but the stored
    # GUID scheme is unknown (legacy content-hash). A version-triggered re-import
    # must run the one-time cleanup and NOT duplicate the deck.
    col = _fresh(tmp_path)
    ai._import_bundled(col)
    single = col.card_count()
    assert single > 5000
    col.set_config(ai._CONFIG_KEY, "2020-01-01")  # force a re-import
    col.remove_config(ai._GUID_SCHEME_KEY)  # pretend the scheme was never stamped
    ai._import_bundled(col)
    assert col.card_count() == single, (
        f"pre-uid re-import duplicated the deck: {single} -> {col.card_count()}"
    )
    assert col.get_config(ai._GUID_SCHEME_KEY) == ai._GUID_SCHEME
    col.close()


def test_uid_reimport_updates_in_place(tmp_path):
    # With the scheme already uid, a re-import matches by GUID: no cleanup, no dup.
    col = _fresh(tmp_path)
    ai._import_bundled(col)
    single = col.card_count()
    col.set_config(ai._CONFIG_KEY, "2020-01-01")  # force a re-import
    ai._import_bundled(col)
    assert col.card_count() == single, (
        f"uid re-import changed card count: {single} -> {col.card_count()}"
    )
    col.close()
