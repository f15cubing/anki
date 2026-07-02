// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { expect, test } from "vitest";

import { formatClock, tally } from "./lib";

test("formatClock renders H:MM:SS and clamps at zero", () => {
    expect(formatClock(170 * 60)).toBe("2:50:00");
    expect(formatClock(59)).toBe("0:00:59");
    expect(formatClock(3661)).toBe("1:01:01");
    expect(formatClock(-5)).toBe("0:00:00");
});

test("tally counts answered / unanswered / marked", () => {
    const t = tally(11, { a: 0, b: 3, c: null }, ["b"]);
    expect(t).toEqual({ answered: 2, unanswered: 9, marked: 1, total: 11 });
});

test("tally with no answers", () => {
    expect(tally(5, {}, [])).toEqual({
        answered: 0,
        unanswered: 5,
        marked: 0,
        total: 5,
    });
});
