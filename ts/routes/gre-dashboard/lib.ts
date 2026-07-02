// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Pure geometry + formatting for the CalibrationStrip signature component.
// Kept dependency-free so it is unit-testable (see lib.test.ts) and so the
// strip can never imply more certainty than the data carries: a null point
// yields an explicit `empty` result rather than a fabricated position.

export interface StripGeometry {
    /** true when there is no point estimate (e.g. n=0) — render the "not yet" rail. */
    empty: boolean;
    /** 0..100 position of the point tick along the axis. */
    tickPct: number;
    /** 0..100 left edge of the confidence band. */
    bandLeftPct: number;
    /** 0..100 width of the confidence band. */
    bandWidthPct: number;
}

function clamp(value: number, lo: number, hi: number): number {
    return Math.min(hi, Math.max(lo, value));
}

/**
 * Map a `{point, low, high}` estimate onto a 0..100 axis spanning `[min, max]`.
 *
 * - `point == null` (or a degenerate axis) → `empty` (no tick, no band).
 * - Missing bounds collapse to the point (zero-width band).
 * - Reversed bounds are normalised; everything is clamped to the axis.
 */
export function stripGeometry(
    point: number | null | undefined,
    low: number | null | undefined,
    high: number | null | undefined,
    min = 0,
    max = 1,
): StripGeometry {
    const span = max - min;
    if (point == null || !(span > 0)) {
        return { empty: true, tickPct: 0, bandLeftPct: 0, bandWidthPct: 0 };
    }
    const norm = (value: number): number => clamp(((value - min) / span) * 100, 0, 100);

    let lo = low ?? point;
    let hi = high ?? point;
    if (hi < lo) {
        [lo, hi] = [hi, lo];
    }
    const bandLeftPct = norm(lo);
    const bandWidthPct = Math.max(0, norm(hi) - bandLeftPct);
    return { empty: false, tickPct: norm(point), bandLeftPct, bandWidthPct };
}

/** Format an axis value for display: a 0..1 proportion as a percent, or a raw score rounded. */
export function formatValue(value: number, scale: "pct" | "raw"): string {
    return scale === "pct" ? `${Math.round(value * 100)}%` : `${Math.round(value)}`;
}
