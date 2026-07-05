# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Desktop-reviewer lockdown for graded MCQ cards: a wrong answer grades Again only.

The bundled "GRE Math MCQ" card template (see ``pipeline/build_deck.py``) reports the
tapped option's correctness to the reviewer via a bridge command
(``pycmd("gremcq:right")`` / ``pycmd("gremcq:wrong")``) the moment the learner taps.
The reviewer stores that verdict for the current card and uses these **pure** helpers
to enforce the study rule "a wrong multiple-choice answer is a lapse":

* :func:`restrict_answer_buttons` collapses the bottom answer-button bar to **Again**
  only after a wrong MCQ, so Hard/Good/Easy aren't even shown via "Show Answer"; and
* :func:`clamp_ease` forces any grade the learner still triggers (button, keyboard
  shortcut, or auto-advance) to **Again(1)**.

It never touches non-MCQ cards (no verdict signalled → ``None`` → no restriction) or a
*correct* MCQ (Hard/Good/Easy preserved — FSRS still needs the difficulty rating). The
in-card graded flow already offers only a single Again on a wrong tap; this closes the
one remaining desktop path (the built-in bottom bar / keyboard) so the rule holds
everywhere. Pure and dependency-free so it unit-tests without a running app; the
reviewer seams are thin wiring.
"""

from __future__ import annotations

from collections.abc import Sequence

# Bridge-command prefix the MCQ template uses to report tap correctness.
PREFIX = "gremcq:"
RIGHT = "right"
WRONG = "wrong"


def parse_verdict(url: str) -> str | None:
    """Return ``"right"``/``"wrong"`` for a ``gremcq:`` bridge command, else ``None``.

    Unknown payloads return ``None`` (treated as "no verdict"), so a malformed signal
    can never accidentally lock or unlock grading.
    """
    if not url.startswith(PREFIX):
        return None
    value = url[len(PREFIX) :]
    return value if value in (RIGHT, WRONG) else None


def should_reveal_synchronously(verdict: str | None, state: str | None) -> bool:
    """Whether an ``ans`` bridge command must reveal the answer *synchronously*.

    The graded MCQ template grades in one tap: after the learner picks an option
    (which records ``verdict`` via ``gremcq:right``/``gremcq:wrong``), the in-card
    rating fires ``pycmd("ans")`` then ``pycmd("ease<N>")`` back to back. The normal
    ``ans`` path reveals the answer *asynchronously* (``evalWithCallback``), so
    ``state`` is still ``"question"`` when the ``ease`` grade arrives and
    ``_answerCard`` silently drops it (it requires ``state == "answer"``) — the
    learner then has to grade a second time on the built-in bottom bar.

    When a verdict is already recorded and we're still on the question, the reviewer
    must reveal synchronously so ``state`` is ``"answer"`` before the grade lands.
    Non-MCQ ``ans`` (no verdict → ``None``) keeps the normal async reveal, and a card
    already past the question needs nothing special.
    """
    return verdict is not None and state == "question"


def is_locked(verdict: str | None) -> bool:
    """Whether grading is locked to Again — only after a *wrong* MCQ answer."""
    return verdict == WRONG


def clamp_ease(verdict: str | None, ease: int) -> int:
    """Force Again(1) when locked; otherwise pass ``ease`` through unchanged."""
    return 1 if is_locked(verdict) else ease


def restrict_answer_buttons(
    verdict: str | None, buttons: Sequence[tuple[int, str]]
) -> tuple[tuple[int, str], ...]:
    """When locked, keep only the Again(1) button; otherwise return ``buttons``.

    Defensive: if the incoming bar somehow has no ease-1 entry, the original bar is
    returned unchanged rather than blanked, so a bug here can never leave the reviewer
    with no way to answer.
    """
    result = tuple(buttons)
    if not is_locked(verdict):
        return result
    again = tuple(b for b in result if b[0] == 1)
    return again or result
