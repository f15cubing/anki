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
