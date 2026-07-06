# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Live-reviewer interleaving: reorder the *review* portion of the v3 queue.

This is the desktop reviewer wiring for the pre-registered interleaving feature
(PRD §8, D5). It is a **pure presentation-layer reorder** of the batch the v3
scheduler already returned: it permutes only the ``REVIEW`` cards in the fetched
``QueuedCards`` so consecutive cards are drawn from different confusable clusters,
subject to the displacement bound in :mod:`aqt.gre.interleave`. It **never**:

* writes card scheduling state, the collection, or the undo stack (it only
  reorders an already-returned protobuf batch in memory);
* changes FSRS intervals (the same cards, same states, are shown in a different
  order);
* touches ``NEW`` / ``LEARNING`` cards (those stay in their scheduler slots so
  intraday-learning timing and new-card introduction order are preserved).

It is **off by default** (`col.conf["gre_interleave"]`), so with the flag unset
the reviewer behaves byte-for-byte as upstream (``fetch_limit`` 1, no reorder).
Turning it on is the ablation's *interleaved* arm; off is the *blocked* arm.

The ordering core (`interleave_order`) is the drift-guarded module vendored from
``pipeline/interleave.py``; this file only adapts it to the reviewer's
``QueuedCards`` batch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from anki.notes import NoteId
from anki.scheduler.v3 import QueuedCards
from aqt.gre.interleave import interleave_order

if TYPE_CHECKING:
    from anki.collection import Collection

# Config key in ``col.conf`` (syncs across devices as a user preference).
CONFIG_KEY = "gre_interleave"

# Lookahead window when interleaving is ON. Bounded so the reorder stays a small,
# near-FSRS-order permutation and the per-card fetch cost stays negligible. With
# the flag OFF we keep upstream's fetch_limit of 1 (zero behaviour change).
FETCH_LIMIT_ON = 16
FETCH_LIMIT_OFF = 1

# Minimum number of review cards in the batch before a reorder is worthwhile.
_MIN_REVIEW = 3


def interleave_enabled(col: Collection) -> bool:
    """Whether interleaving is switched on for this collection (default False)."""
    try:
        return bool(col.get_config(CONFIG_KEY, False))
    except Exception:
        return False


def fetch_limit(col: Collection) -> int:
    """How many cards the reviewer should fetch: a lookahead window when ON, else 1."""
    return FETCH_LIMIT_ON if interleave_enabled(col) else FETCH_LIMIT_OFF


def _leaf_tag(col: Collection, note_id: int) -> str | None:
    """The card's ``topic::…`` leaf tag, or None if unavailable."""
    try:
        tags = col.get_note(NoteId(note_id)).tags
    except Exception:
        return None
    for tag in tags:
        if tag.startswith("topic::"):
            return tag
    return None


def reorder_output(col: Collection, output: QueuedCards) -> None:
    """Interleave the REVIEW cards of ``output`` in place. No-op unless enabled.

    Safe by construction: if interleaving is off, the batch is small, there are
    fewer than three review cards, or any review card lacks a ``topic::`` leaf
    tag, the batch is left exactly as the scheduler returned it. ``NEW`` and
    ``LEARNING`` cards keep their positions; only review slots are permuted, and
    each ``QueuedCard`` (card + states + context) moves as a self-contained unit,
    so the shown card is always paired with its own scheduling states.

    The permutation is computed **purely** first (:func:`_interleaved_cards`, no
    mutation); only a successfully-built, non-``None`` result is written back, and
    any unexpected error falls back to the scheduler's original order — an
    interleaving bug can never empty the queue or interrupt review.
    """
    if not interleave_enabled(col):
        return
    try:
        reordered = _interleaved_cards(col, output)
    except Exception:
        return  # never let the opt-in reorder interrupt the review loop
    if reordered is None:
        return  # a no-op case (small/homogeneous/untagged/already-interleaved)
    del output.cards[:]
    output.cards.extend(reordered)


def _interleaved_cards(col: Collection, output: QueuedCards) -> list | None:
    """Pure: return the reordered ``QueuedCard`` list, or ``None`` for a no-op.

    Does not mutate ``output`` — it snapshots each ``QueuedCard`` into a standalone
    message and returns them in the interleaved order, so the caller's write-back
    is the only mutation and happens only after this fully succeeds.
    """
    n = len(output.cards)
    if n < _MIN_REVIEW:
        return None

    review_positions = [
        i for i in range(n) if output.cards[i].queue == QueuedCards.REVIEW
    ]
    if len(review_positions) < _MIN_REVIEW:
        return None

    # (position, leaf) for each review card, in FSRS priority order. Positions
    # double as stable ids for interleave_order.
    pairs: list[tuple[int, str]] = []
    for i in review_positions:
        leaf = _leaf_tag(col, output.cards[i].card.note_id)
        if leaf is None:
            return None  # incomplete tagging → bail out, don't guess
        pairs.append((i, leaf))

    ordered_positions = [pos for pos, _leaf in interleave_order(pairs)]
    if ordered_positions == review_positions:
        return None  # already interleaved / nothing to do

    # Final index order: review slots filled by the interleaved order, everything
    # else untouched.
    final = list(range(n))
    for slot, src in zip(review_positions, ordered_positions):
        final[slot] = src

    # Snapshot each QueuedCard into a standalone message (avoids aliasing the
    # parent-owned messages), then return them in the new order.
    snapshot = []
    for card in output.cards:
        copy = type(card)()
        copy.CopyFrom(card)
        snapshot.append(copy)
    return [snapshot[idx] for idx in final]
