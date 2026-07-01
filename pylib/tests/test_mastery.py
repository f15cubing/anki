# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from tests.shared import getEmptyCol


def _add(col, front, tag):
    note = col.newNote()
    note["Front"] = front
    note["Back"] = "a"
    note.tags.append(tag)
    col.addNote(note)


def test_mastery_query_counts_and_hierarchy():
    col = getEmptyCol()
    for i in range(3):
        _add(col, f"c{i}", "topic::calculus::integral_single")
    _add(col, "alg", "topic::algebra::linear")

    res = col.mastery_query(
        ["topic::calculus", "topic::calculus::integral_single", "topic::algebra"]
    )
    by = {t.topic: t for t in res}
    assert by["topic::calculus::integral_single"].total_cards == 3
    assert by["topic::calculus"].total_cards == 3  # hierarchical rollup
    assert by["topic::algebra"].total_cards == 1
    # brand-new cards have no FSRS memory state
    assert by["topic::calculus"].reviewed_count == 0
    assert by["topic::calculus"].mastered_count == 0
    assert by["topic::calculus"].avg_recall == 0.0
    col.close()


def test_mastery_query_is_read_only_with_undo():
    col = getEmptyCol()
    for i in range(3):
        _add(col, f"c{i}", "topic::calculus::integral_single")

    # add a note, run the mastery query in between, then undo the add
    _add(col, "extra", "topic::calculus::integral_single")
    assert col.mastery_query(["topic::calculus"])[0].total_cards == 4
    # the "Add Note" remains undoable despite the intervening read
    assert col.undo_status().undo
    col.undo()
    assert col.mastery_query(["topic::calculus"])[0].total_cards == 3
    col.close()
