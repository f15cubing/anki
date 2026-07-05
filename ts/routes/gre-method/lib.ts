// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Pure helpers for the interleaving demo on the "how this differs from FSRS" page.
// Kept side-effect-free so they can be unit-tested without a DOM (see lib.test.ts).

// A small palette used to colour confusable clusters (each GRE leaf type). The
// interleaving section spends the page's colour budget here: colour *is* the
// information (you can see same-colour cards spread apart). White text reads on all
// of these in both light and dark mode.
export const CLUSTER_PALETTE = [
    "#0e7c86", // teal (matches the dashboard signal accent)
    "#b26b00", // amber
    "#3b5bdb", // indigo
    "#9c36b5", // grape
    "#2f9e44", // green
    "#c2255c", // rose
];

// Stable colour for a cluster: its position in the queue's cluster order, wrapped
// over the palette. Unknown clusters fall back to the first colour (never throws).
export function colorForCluster(cluster: string, order: string[]): string {
    const i = order.indexOf(cluster);
    const idx = i < 0 ? 0 : i;
    return CLUSTER_PALETTE[idx % CLUSTER_PALETTE.length];
}

// Percentage with no decimals; null/NaN render as an em dash — never a fabricated 0.
export function formatPct(x: number | null | undefined): string {
    if (x == null || Number.isNaN(x)) {
        return "—";
    }
    return `${Math.round(x * 100)}%`;
}

// A plain number to `digits` decimals; null/NaN render as an em dash.
export function formatNum(x: number | null | undefined, digits = 1): string {
    if (x == null || Number.isNaN(x)) {
        return "—";
    }
    return x.toFixed(digits);
}
