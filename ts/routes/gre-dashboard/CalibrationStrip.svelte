<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
The signature element of the dashboard: a single estimate rendered as a shaded
95% confidence band with a point tick on a 0..max axis. Used at every scale
(exam headline, per-bucket, per-leaf), so "we show a range, never a fabricated
point" is the visual language of the page. When there is no estimate (n=0) it
draws an explicit dotted "not yet" rail instead of pretending to a position.
-->
<script lang="ts">
    import { formatValue, stripGeometry } from "./lib";

    interface Props {
        point: number | null;
        low?: number | null;
        high?: number | null;
        n?: number | null;
        min?: number;
        max?: number;
        scale?: "pct" | "raw";
        tone?: "signal" | "abstain";
        compact?: boolean;
        label?: string;
        emptyLabel?: string;
        /** faint right-aligned annotation, e.g. the estimator: "Wilson", "Platt". */
        method?: string | null;
    }

    const {
        point,
        low = null,
        high = null,
        n = null,
        min = 0,
        max = 1,
        scale = "pct",
        tone = "signal",
        compact = false,
        label = "",
        emptyLabel = "not studied yet",
        method = null,
    }: Props = $props();

    const geo = $derived(stripGeometry(point, low, high, min, max));
    const fmt = (v: number | null | undefined): string =>
        v == null ? "—" : formatValue(v, scale);
    // Bare bound (no unit) so the interval reads like CAS output: 60% ∈ [54, 66].
    function fmtBound(v: number | null | undefined): string {
        if (v == null) {
            return "—";
        }
        return scale === "pct" ? `${Math.round(v * 100)}` : `${Math.round(v)}`;
    }
</script>

<div class="strip {tone}" class:compact class:empty={geo.empty}>
    {#if label}
        <div class="label">{label}</div>
    {/if}
    <div
        class="track"
        role="meter"
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={geo.empty ? undefined : point}
        aria-label={label || "estimate"}
    >
        {#if !geo.empty}
            <div
                class="band"
                style="left:{geo.bandLeftPct}%;width:{geo.bandWidthPct}%"
            ></div>
            <div class="tick" style="left:{geo.tickPct}%"></div>
        {/if}
    </div>
    <div class="readout">
        {#if geo.empty}
            <span class="muted">{emptyLabel}</span>
        {:else}
            <span class="point">{fmt(point)}</span>
            <span class="ci">∈ [{fmtBound(low)}, {fmtBound(high)}]</span>
            {#if n != null}
                <span class="n">n={n}</span>
            {/if}
            {#if method}
                <span class="method">{method}</span>
            {/if}
        {/if}
    </div>
</div>

<style>
    .strip {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
    }
    .label {
        font-size: var(--gre-fs-body);
        color: var(--gre-ink);
    }
    .track {
        position: relative;
        height: 12px;
        border-radius: 999px;
        background: var(--gre-surface-sunk);
        border: 1px solid var(--gre-hairline);
        overflow: hidden;
    }
    .compact .track {
        height: 8px;
    }
    .band {
        position: absolute;
        top: 0;
        bottom: 0;
        background: var(--gre-band);
        transition:
            left 0.25s ease,
            width 0.25s ease;
    }
    .tick {
        position: absolute;
        top: -1px;
        bottom: -1px;
        width: 2px;
        transform: translateX(-1px);
        background: var(--gre-signal);
        transition: left 0.25s ease;
    }
    .abstain .tick {
        background: var(--gre-abstain);
    }
    .abstain .band {
        background: var(--gre-abstain-band);
    }
    .method {
        margin-left: auto;
        color: var(--gre-faint);
        font-size: 0.62rem;
        letter-spacing: 0.04em;
    }
    .empty .track {
        background: repeating-linear-gradient(
            90deg,
            transparent 0 5px,
            var(--gre-hairline) 5px 7px
        );
        border-style: dashed;
    }
    .readout {
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
        font-family: var(--gre-mono);
        font-variant-numeric: tabular-nums;
        font-size: var(--gre-fs-body);
    }
    .point {
        color: var(--gre-ink);
        font-weight: 600;
        font-size: var(--gre-fs-figure);
    }
    .compact .point {
        font-size: var(--gre-fs-body);
    }
    .ci,
    .n {
        color: var(--gre-muted);
        font-size: 0.8rem;
    }
    .muted {
        color: var(--gre-muted);
        font-family: var(--gre-sans);
        font-size: var(--gre-fs-body);
    }

    @media (prefers-reduced-motion: reduce) {
        .band,
        .tick {
            transition: none;
        }
    }
</style>
