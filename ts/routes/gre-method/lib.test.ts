// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { expect, test } from "vitest";

import { CLUSTER_PALETTE, colorForCluster, formatNum, formatPct } from "./lib";

const order = ["a", "b", "c", "d"];

test("colorForCluster maps by queue position and is stable", () => {
    expect(colorForCluster("a", order)).toBe(CLUSTER_PALETTE[0]);
    expect(colorForCluster("c", order)).toBe(CLUSTER_PALETTE[2]);
    expect(colorForCluster("b", order)).toBe(colorForCluster("b", order));
});

test("colorForCluster wraps around the palette", () => {
    const many = Array.from({ length: CLUSTER_PALETTE.length + 2 }, (_, i) => `c${i}`);
    // the (palette.length)-th cluster wraps back to the first colour
    expect(colorForCluster(many[CLUSTER_PALETTE.length], many)).toBe(CLUSTER_PALETTE[0]);
});

test("colorForCluster falls back to the first colour for an unknown cluster", () => {
    expect(colorForCluster("zzz", order)).toBe(CLUSTER_PALETTE[0]);
});

test("formatPct renders whole percentages", () => {
    expect(formatPct(0.96)).toBe("96%");
    expect(formatPct(0)).toBe("0%");
    expect(formatPct(0.244)).toBe("24%");
});

test("formatters never fabricate a number for null/NaN", () => {
    expect(formatPct(null)).toBe("—");
    expect(formatPct(undefined)).toBe("—");
    expect(formatNum(null)).toBe("—");
    expect(formatNum(NaN)).toBe("—");
});

test("formatNum honours the requested precision", () => {
    expect(formatNum(1.5)).toBe("1.5");
    expect(formatNum(2, 0)).toBe("2");
});
