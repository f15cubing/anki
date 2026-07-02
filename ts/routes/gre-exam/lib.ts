// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Pure client helpers for the exam shell (unit-tested in lib.test.ts).

export const OPTION_LETTERS = ["A", "B", "C", "D", "E"];

/** Whole-session countdown as H:MM:SS (clamped at zero). */
export function formatClock(totalSeconds: number): string {
    const s = Math.max(0, Math.floor(totalSeconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${h}:${pad(m)}:${pad(sec)}`;
}

export interface Tally {
    answered: number;
    unanswered: number;
    marked: number;
    total: number;
}

/** Count answered / unanswered / marked for the review screen + header. */
export function tally(
    total: number,
    answers: Record<string, number | null | undefined>,
    marked: string[],
): Tally {
    let answered = 0;
    for (const v of Object.values(answers)) {
        if (v !== null && v !== undefined) {
            answered += 1;
        }
    }
    return { answered, unanswered: total - answered, marked: marked.length, total };
}
