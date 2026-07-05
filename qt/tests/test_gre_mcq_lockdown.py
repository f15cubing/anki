# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Tests for the graded-MCQ wrong-answer lockdown + bundled-template refresh.

Two independently-testable pieces, both without a running app:

* ``aqt.gre.mcq_lockdown`` — the pure helpers the reviewer seams call: parse the tap
  verdict, clamp a wrong answer's grade to Again, and collapse the answer bar to
  Again only.
* ``aqt.gre.deck_autoimport`` — the in-place note-type template refresh that gets a
  new template onto EXISTING installs (gated by a template-revision key), proven with
  stubs (no real ``.apkg`` / collection needed).

The live GUI click-through — a wrong MCQ offers only Again on the built-in bottom bar
and keyboard 2/3/4 no longer grade it Hard/Good/Easy — is the one human smoke step.
"""

# Import collection first so the anki backend is initialised before we import the
# aqt helpers (mirrors test_gre_interleave_review.py; avoids a harness-only import
# ordering issue).
import anki.collection  # noqa: F401
from aqt.gre import deck_autoimport
from aqt.gre.mcq_lockdown import (
    clamp_ease,
    is_locked,
    parse_verdict,
    restrict_answer_buttons,
)

FOUR = ((1, "Again"), (2, "Hard"), (3, "Good"), (4, "Easy"))


# --- pure lockdown helpers ---------------------------------------------------


def test_parse_verdict_recognises_right_and_wrong():
    assert parse_verdict("gremcq:right") == "right"
    assert parse_verdict("gremcq:wrong") == "wrong"


def test_parse_verdict_ignores_other_or_malformed_urls():
    for url in ("ease3", "ans", "gremcq:", "gremcq:maybe", "gremcqwrong", ""):
        assert parse_verdict(url) is None


def test_is_locked_only_on_wrong():
    assert is_locked("wrong") is True
    assert is_locked("right") is False
    assert is_locked(None) is False


def test_clamp_ease_forces_again_only_when_wrong():
    for ease in (1, 2, 3, 4):
        assert clamp_ease("wrong", ease) == 1  # every rating becomes Again
    for verdict in ("right", None):  # correct + non-MCQ pass through untouched
        for ease in (1, 2, 3, 4):
            assert clamp_ease(verdict, ease) == ease


def test_restrict_answer_buttons_wrong_keeps_only_again():
    assert restrict_answer_buttons("wrong", FOUR) == ((1, "Again"),)


def test_restrict_answer_buttons_correct_and_none_unchanged():
    assert restrict_answer_buttons("right", FOUR) == FOUR
    assert restrict_answer_buttons(None, FOUR) == FOUR


def test_restrict_answer_buttons_never_blanks_the_bar():
    # Defensive: a bar with no ease-1 entry is returned unchanged, not emptied.
    weird = ((2, "Hard"), (3, "Good"))
    assert restrict_answer_buttons("wrong", weird) == weird


# --- bundled-template refresh (deck_autoimport) ------------------------------


class _StubModels:
    def __init__(self, notetypes):
        self._by_name = {nt["name"]: nt for nt in notetypes}
        self.updated: list[str] = []

    def by_name(self, name):
        return self._by_name.get(name)

    def update_dict(self, nt):
        self.updated.append(nt["name"])


class _StubCol:
    def __init__(self, notetypes, conf=None):
        self.models = _StubModels(notetypes)
        self._conf = dict(conf or {})

    def get_config(self, key, default=None):
        return self._conf.get(key, default)

    def set_config(self, key, value):
        self._conf[key] = value


_MCQ_NAME = deck_autoimport._BUNDLED_NOTETYPES[1]


def _bundled_json(qfmt="NEW-Q", afmt="NEW-A", css="NEW-CSS"):
    """A legacy-schema ``col.models`` blob (keyed by model id) for the MCQ type."""
    return {
        "1": {
            "name": _MCQ_NAME,
            "css": css,
            "tmpls": [{"ord": 0, "qfmt": qfmt, "afmt": afmt}],
        }
    }


def _live_mcq(qfmt="OLD-Q", afmt="OLD-A", css="OLD-CSS"):
    return {
        "name": _MCQ_NAME,
        "css": css,
        "tmpls": [{"ord": 0, "qfmt": qfmt, "afmt": afmt}],
    }


def test_refresh_updates_stale_template_in_place(monkeypatch):
    monkeypatch.setattr(deck_autoimport, "_bundled_models_json", _bundled_json)
    live = _live_mcq()
    col = _StubCol([live])
    deck_autoimport._refresh_bundled_notetype_templates(col)
    assert live["css"] == "NEW-CSS"
    assert live["tmpls"][0]["qfmt"] == "NEW-Q"
    assert live["tmpls"][0]["afmt"] == "NEW-A"
    assert col.models.updated == [_MCQ_NAME]  # persisted exactly once


def test_refresh_is_noop_when_already_current(monkeypatch):
    monkeypatch.setattr(deck_autoimport, "_bundled_models_json", _bundled_json)
    col = _StubCol([_live_mcq(qfmt="NEW-Q", afmt="NEW-A", css="NEW-CSS")])
    deck_autoimport._refresh_bundled_notetype_templates(col)
    assert col.models.updated == []  # nothing changed → no write


def test_refresh_skips_absent_notetype(monkeypatch):
    monkeypatch.setattr(deck_autoimport, "_bundled_models_json", _bundled_json)
    col = _StubCol([])  # note type not installed on this profile
    deck_autoimport._refresh_bundled_notetype_templates(col)
    assert col.models.updated == []


def test_refresh_degrades_to_noop_when_apkg_unreadable(monkeypatch):
    monkeypatch.setattr(deck_autoimport, "_bundled_models_json", lambda: None)
    col = _StubCol([_live_mcq()])
    deck_autoimport._refresh_bundled_notetype_templates(col)  # must not raise
    assert col.models.updated == []


def test_templates_up_to_date_gate():
    assert deck_autoimport._templates_up_to_date(_StubCol([])) is False
    current = _StubCol(
        [],
        conf={
            deck_autoimport._TEMPLATE_REVISION_KEY: deck_autoimport._TEMPLATE_REVISION
        },
    )
    assert deck_autoimport._templates_up_to_date(current) is True


def test_run_if_needed_refreshes_templates_without_reimport(monkeypatch):
    # Existing install: deck version + GUID scheme current, but the template revision
    # is stale → templates refresh in place (no deck re-import) and the revision key
    # gets stamped so it runs only once.
    monkeypatch.setattr(deck_autoimport, "_bundled_models_json", _bundled_json)
    imported: list[bool] = []
    monkeypatch.setattr(
        deck_autoimport, "_import_bundled", lambda col: imported.append(True)
    )
    col = _StubCol(
        [_live_mcq()],
        conf={
            deck_autoimport._CONFIG_KEY: deck_autoimport.GRE_DECK_VERSION,
            deck_autoimport._GUID_SCHEME_KEY: deck_autoimport._GUID_SCHEME,
        },
    )
    ran = deck_autoimport._run_if_needed(col)
    assert ran is True
    assert imported == []  # deck content NOT re-imported
    assert col.models.updated == [_MCQ_NAME]  # template refreshed in place
    assert (
        col.get_config(deck_autoimport._TEMPLATE_REVISION_KEY)
        == deck_autoimport._TEMPLATE_REVISION
    )
