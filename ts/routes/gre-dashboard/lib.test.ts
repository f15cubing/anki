// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { expect, test } from "vitest";

import { formatValue, stripGeometry } from "./lib";

test("point maps to a centred tick with a spanning band", () => {
    const g = stripGeometry(0.5, 0.4, 0.6);
    expect(g.empty).toBe(false);
    expect(g.tickPct).toBeCloseTo(50);
    expect(g.bandLeftPct).toBeCloseTo(40);
    expect(g.bandWidthPct).toBeCloseTo(20);
});

test("null point yields an empty rail, never a fabricated position", () => {
    const g = stripGeometry(null, null, null);
    expect(g).toEqual({ empty: true, tickPct: 0, bandLeftPct: 0, bandWidthPct: 0 });
});

test("missing bounds collapse to a zero-width band at the point", () => {
    const g = stripGeometry(0.7, null, null);
    expect(g.empty).toBe(false);
    expect(g.tickPct).toBeCloseTo(70);
    expect(g.bandWidthPct).toBeCloseTo(0);
});

test("reversed bounds are normalised", () => {
    const g = stripGeometry(0.5, 0.6, 0.4);
    expect(g.bandLeftPct).toBeCloseTo(40);
    expect(g.bandWidthPct).toBeCloseTo(20);
});

test("values are clamped to the axis", () => {
    const g = stripGeometry(1.5, -0.2, 2);
    expect(g.tickPct).toBe(100);
    expect(g.bandLeftPct).toBe(0);
    expect(g.bandWidthPct).toBe(100);
});

test("degenerate axis is treated as empty", () => {
    expect(stripGeometry(0.5, 0.4, 0.6, 1, 1).empty).toBe(true);
});

test("raw scale maps onto a custom domain (readiness 200..990)", () => {
    const g = stripGeometry(595, 540, 650, 200, 990);
    expect(g.tickPct).toBeCloseTo(50, 0);
    expect(g.bandLeftPct).toBeGreaterThan(40);
    expect(g.bandWidthPct).toBeGreaterThan(0);
});

test("formatValue renders percent or raw", () => {
    expect(formatValue(0.62, "pct")).toBe("62%");
    expect(formatValue(594.6, "raw")).toBe("595");
});
