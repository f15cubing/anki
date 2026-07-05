# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Tests for live-reviewer interleaving (aqt.gre.interleave_review).

These cover the pure reorder helper without a running app: the flag gate, the
fetch-limit switch, the review-only permutation, the safe fallbacks, and the
load-bearing multiset invariant (nothing added/dropped/duplicated). The live GUI
click-through (flip the toggle mid-review) is the one human smoke step.
"""

# Import collection first so anki.scheduler.base is fully initialised before we
# pull in anki.scheduler.v3 (avoids a harness-only circular import; in the app the
# helper is imported lazily at review time, well after the collection is loaded).
import anki.collection  # noqa: F401
from anki.scheduler.v3 import QueuedCards
from aqt.gre.interleave_review import (
    CONFIG_KEY,
    FETCH_LIMIT_OFF,
    FETCH_LIMIT_ON,
    fetch_limit,
    interleave_enabled,
    reorder_output,
)

CALC_A = "topic::calculus::differential_single"
CALC_B = "topic::calculus::integral_single"


class _StubNote:
    def __init__(self, tags):
        self.tags = tags


class _StubCol:
    """Minimal Collection stand-in: get_config + get_note over an in-memory map."""

    def __init__(self, enabled, tags_by_nid):
        self._enabled = enabled
        self._tags_by_nid = tags_by_nid

    def get_config(self, key, default=None):
        if key == CONFIG_KEY:
            return self._enabled
        return default

    def get_note(self, note_id):
        return _StubNote(self._tags_by_nid[note_id])


# A distinctive per-card marker stamped into each QueuedCard's *context* sub-message
# (context.seed = _SEED_BASE + note_id). Lets a test prove the whole QueuedCard —
# card + states + context — moves as a self-contained unit through the reorder.
_SEED_BASE = 900000


def _mk_output(cards):
    """cards: list of (queue, note_id[, leaf]) → a QueuedCards proto batch."""
    out = QueuedCards()
    for i, spec in enumerate(cards):
        queue, nid = spec[0], spec[1]
        qc = out.cards.add()
        qc.queue = queue
        qc.card.id = 1000 + i
        qc.card.note_id = nid
        qc.context.seed = (
            _SEED_BASE + nid
        )  # travels with the card iff units stay intact
    return out


def _order(out):
    return [(qc.queue, qc.card.note_id) for qc in out.cards]


def _tags(*specs):
    return {nid: [leaf] for nid, leaf in specs}


def _adjacent_same_leaf(out, tags_by_nid):
    """Count consecutive REVIEW pairs whose leaf tag matches (blocked-ness proxy)."""
    review_leaves = [
        tags_by_nid[qc.card.note_id][0]
        for qc in out.cards
        if qc.queue == QueuedCards.REVIEW
    ]
    return sum(1 for a, b in zip(review_leaves, review_leaves[1:]) if a == b)


# --- flag gate + fetch limit -------------------------------------------------


def test_disabled_is_a_noop():
    tags = _tags(
        (1, CALC_A), (2, CALC_A), (3, CALC_A), (4, CALC_B), (5, CALC_B), (6, CALC_B)
    )
    col = _StubCol(enabled=False, tags_by_nid=tags)
    out = _mk_output([(QueuedCards.REVIEW, n) for n in (1, 2, 3, 4, 5, 6)])
    before = _order(out)
    reorder_output(col, out)
    assert _order(out) == before  # byte-identical when off


def test_fetch_limit_switches_with_flag():
    tags = _tags((1, CALC_A))
    assert fetch_limit(_StubCol(True, tags)) == FETCH_LIMIT_ON
    assert fetch_limit(_StubCol(False, tags)) == FETCH_LIMIT_OFF
    assert FETCH_LIMIT_OFF == 1  # OFF must equal upstream default


def test_interleave_enabled_default_false_and_error_safe():
    tags = _tags((1, CALC_A))
    assert interleave_enabled(_StubCol(True, tags)) is True
    assert interleave_enabled(_StubCol(False, tags)) is False

    class _Boom:
        def get_config(self, *a, **k):
            raise RuntimeError("boom")

    assert interleave_enabled(_Boom()) is False  # never raises into the reviewer


# --- reordering behaviour ----------------------------------------------------


def test_enabled_disperses_blocked_reviews():
    tags = _tags(
        (1, CALC_A), (2, CALC_A), (3, CALC_A), (4, CALC_B), (5, CALC_B), (6, CALC_B)
    )
    col = _StubCol(enabled=True, tags_by_nid=tags)
    out = _mk_output([(QueuedCards.REVIEW, n) for n in (1, 2, 3, 4, 5, 6)])
    same_before = _adjacent_same_leaf(out, tags)  # blocked → 4
    reorder_output(col, out)
    same_after = _adjacent_same_leaf(out, tags)
    assert same_after < same_before  # interleaving reduced same-cluster adjacency


def test_multiset_invariant():
    tags = _tags(
        (1, CALC_A), (2, CALC_A), (3, CALC_A), (4, CALC_B), (5, CALC_B), (6, CALC_B)
    )
    col = _StubCol(enabled=True, tags_by_nid=tags)
    out = _mk_output([(QueuedCards.REVIEW, n) for n in (1, 2, 3, 4, 5, 6)])
    before = sorted(_order(out))
    reorder_output(col, out)
    assert sorted(_order(out)) == before  # nothing added / dropped / duplicated


def test_states_and_context_travel_with_card():
    # The load-bearing safety invariant: each QueuedCard (card + states + context)
    # must move as a self-contained unit, so the shown card is paired with its own
    # scheduling data. We stamp context.seed = _SEED_BASE + note_id and assert it
    # still holds for every card after the reorder actually permutes the batch.
    tags = _tags(
        (1, CALC_A), (2, CALC_A), (3, CALC_A), (4, CALC_B), (5, CALC_B), (6, CALC_B)
    )
    col = _StubCol(enabled=True, tags_by_nid=tags)
    out = _mk_output([(QueuedCards.REVIEW, n) for n in (1, 2, 3, 4, 5, 6)])
    before = _order(out)
    reorder_output(col, out)
    assert _order(out) != before  # the reorder really happened
    for qc in out.cards:
        assert qc.context.seed == _SEED_BASE + qc.card.note_id


def test_new_and_learning_keep_their_positions():
    tags = _tags((1, CALC_A), (2, CALC_A), (3, CALC_B), (4, CALC_B))
    col = _StubCol(enabled=True, tags_by_nid=tags)
    out = _mk_output(
        [
            (QueuedCards.NEW, 90),
            (QueuedCards.REVIEW, 1),
            (QueuedCards.REVIEW, 2),
            (QueuedCards.REVIEW, 3),
            (QueuedCards.REVIEW, 4),
            (QueuedCards.LEARNING, 91),
        ]
    )
    reorder_output(col, out)
    order = _order(out)
    assert order[0] == (QueuedCards.NEW, 90)
    assert order[-1] == (QueuedCards.LEARNING, 91)
    # the review block is a permutation of the four review cards
    assert sorted(order[1:5]) == sorted([(QueuedCards.REVIEW, n) for n in (1, 2, 3, 4)])


def test_too_few_review_cards_is_a_noop():
    tags = _tags((1, CALC_A), (2, CALC_B))
    col = _StubCol(enabled=True, tags_by_nid=tags)
    out = _mk_output([(QueuedCards.REVIEW, 1), (QueuedCards.REVIEW, 2)])
    before = _order(out)
    reorder_output(col, out)
    assert _order(out) == before


def test_homogeneous_cluster_is_a_noop():
    tags = _tags((1, CALC_A), (2, CALC_A), (3, CALC_A), (4, CALC_A))
    col = _StubCol(enabled=True, tags_by_nid=tags)
    out = _mk_output([(QueuedCards.REVIEW, n) for n in (1, 2, 3, 4)])
    before = _order(out)
    reorder_output(col, out)
    assert _order(out) == before  # nothing to disperse → unchanged


def test_missing_topic_tag_bails_out_safely():
    # card 3 has no topic:: tag → the whole batch is left untouched.
    tags = {1: [CALC_A], 2: [CALC_B], 3: ["marked"], 4: [CALC_B]}
    col = _StubCol(enabled=True, tags_by_nid=tags)
    out = _mk_output([(QueuedCards.REVIEW, n) for n in (1, 2, 3, 4)])
    before = _order(out)
    reorder_output(col, out)
    assert _order(out) == before
