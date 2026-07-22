<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
The interactive centrepiece: it POSTs to the read-only greMethodInterleave endpoint,
which runs the REAL vendored interleave.py on a fixed example queue, and shows the
blocked (FSRS) order vs the interleaved order as colour-by-type chips, with the two
metrics the algorithm reports. The K/W sliders re-run the actual algorithm.
-->
<script lang="ts">
    import { flip } from "svelte/animate";

    import { colorForCluster, formatNum, formatPct } from "./lib";

    let k = $state(1);
    let w = $state(3);
    let demo = $state<any>(null);
    let error = $state("");

    const reduced =
        typeof window !== "undefined" &&
        !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    async function post(endpoint: string, body: unknown): Promise<any> {
        // mediasrv 403s any POST whose Content-Type isn't application/binary (before
        // auth) — same convention as the dashboard/exam pages. The JSON body rides in
        // the request bytes; the server parses it with get_json(force=True).
        const resp = await fetch(`/_anki/${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/binary" },
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        return resp.json();
    }

    async function reload() {
        try {
            demo = await post("greMethodInterleave", { k, w });
            error = "";
        } catch (e) {
            error = String(e);
        }
    }

    // Initial load + debounced re-run whenever K or W change (each run is the real
    // Python algorithm, so debounce the slider drag).
    let timer: ReturnType<typeof setTimeout> | null = null;
    $effect(() => {
        void k;
        void w;
        if (timer) {
            clearTimeout(timer);
        }
        timer = setTimeout(reload, 90);
        return () => {
            if (timer) {
                clearTimeout(timer);
            }
        };
    });

    const clusterOrder = $derived(
        (demo?.clusters ?? []).map((c: any) => c.cluster as string),
    );
    const metrics = $derived(demo?.metrics ?? null);
    const flipDur = reduced ? 0 : 260;
</script>

<div class="il">
    <div class="controls">
        <label class="ctrl">
            <span class="ctrl-label">
                Avoid last <b>{k}</b>
                type{k === 1 ? "" : "s"}
            </span>
            <input
                type="range"
                min="0"
                max="5"
                bind:value={k}
                aria-label="K: clusters to avoid"
            />
            <span class="ctrl-key">K</span>
        </label>
        <label class="ctrl">
            <span class="ctrl-label">
                Max wait <b>{w}</b>
                slot{w === 1 ? "" : "s"}
            </span>
            <input
                type="range"
                min="1"
                max="12"
                bind:value={w}
                aria-label="W: displacement bound"
            />
            <span class="ctrl-key">W</span>
        </label>
    </div>

    {#if error}
        <p class="err">Couldn't run the demo — {error}.</p>
    {:else if !demo}
        <p class="muted">Running the algorithm…</p>
    {:else}
        <div class="rows">
            <div class="row">
                <span class="rlabel">
                    Blocked <em>· FSRS order</em>
                </span>
                <div class="chips">
                    {#each demo.blocked as chip (chip.id)}
                        <span
                            class="chip"
                            style="background:{colorForCluster(
                                chip.cluster,
                                clusterOrder,
                            )}"
                        >
                            {chip.label}
                        </span>
                    {/each}
                </div>
            </div>
            <div class="row">
                <span class="rlabel accent">Interleaved</span>
                <div class="chips">
                    {#each demo.interleaved as chip (chip.id)}
                        <span
                            class="chip"
                            animate:flip={{ duration: flipDur }}
                            style="background:{colorForCluster(
                                chip.cluster,
                                clusterOrder,
                            )}"
                        >
                            {chip.label}
                        </span>
                    {/each}
                </div>
            </div>
        </div>

        <div class="metrics">
            <div class="metric">
                <span class="mlabel">Adjacency dispersion</span>
                <span class="mval">
                    {formatPct(metrics.blocked_dispersion)}
                    <span class="arrow">→</span>
                    <b>{formatPct(metrics.adjacency_dispersion)}</b>
                </span>
                <span class="mhint">neighbours that are a different type</span>
            </div>
            <div class="metric">
                <span class="mlabel">FSRS displacement</span>
                <span class="mval">
                    mean {formatNum(metrics.displacement_mean)} · max
                    <b>{metrics.displacement_max}</b>
                </span>
                <span class="mhint">
                    slots a card waits past its FSRS place (≤ W = {w})
                </span>
            </div>
        </div>

        {#if metrics.used_fallback}
            <p class="muted small">
                This queue is too homogeneous to disperse — the algorithm falls back to
                plain FSRS order (nothing is forced).
            </p>
        {/if}

        <p class="invariant">
            Same cards, reordered. The shown set always equals the FSRS due set —
            scheduling fields are never touched — and no card waits more than <b>W</b>
            slots, so urgent cards can't starve.
        </p>

        <div class="legend">
            {#each demo.clusters as c}
                <span class="lg">
                    <span
                        class="dot"
                        style="background:{colorForCluster(c.cluster, clusterOrder)}"
                    ></span>
                    {c.label}
                </span>
            {/each}
        </div>
    {/if}
</div>

<style>
    .il {
        border: 1px solid var(--gre-hairline);
        border-radius: var(--gre-radius);
        background: var(--gre-surface);
        padding: 1.1rem 1.25rem 1.25rem;
    }
    .controls {
        display: flex;
        flex-wrap: wrap;
        gap: 1.5rem;
        padding-bottom: 1rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid var(--gre-hairline);
    }
    .ctrl {
        display: grid;
        grid-template-columns: auto 1fr auto;
        align-items: center;
        gap: 0.55rem;
        min-width: 240px;
        flex: 1;
    }
    .ctrl-label {
        font-size: 0.85rem;
        color: var(--gre-muted);
        white-space: nowrap;
    }
    .ctrl-label b {
        color: var(--gre-ink);
        font-family: var(--gre-mono);
        font-variant-numeric: tabular-nums;
    }
    .ctrl input[type="range"] {
        width: 100%;
        accent-color: var(--gre-signal);
    }
    .ctrl-key {
        font-family: var(--gre-mono);
        font-size: 0.72rem;
        color: var(--gre-signal);
        border: 1px solid var(--gre-hairline);
        border-radius: 5px;
        padding: 0.05rem 0.35rem;
    }
    .rows {
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
    }
    .row {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }
    .rlabel {
        font-family: var(--gre-mono);
        font-size: 0.74rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--gre-muted);
    }
    .rlabel em {
        font-style: normal;
        opacity: 0.7;
    }
    .rlabel.accent {
        color: var(--gre-signal);
    }
    .chips {
        display: flex;
        flex-wrap: wrap;
        gap: 0.3rem;
    }
    .chip {
        color: #fff;
        font-size: 0.78rem;
        font-weight: 600;
        line-height: 1;
        padding: 0.4rem 0.55rem;
        border-radius: 6px;
        white-space: nowrap;
    }
    .metrics {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.8rem;
        margin-top: 1.15rem;
    }
    .metric {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        padding: 0.7rem 0.85rem;
        border: 1px solid var(--gre-hairline);
        border-radius: 8px;
        background: var(--gre-surface-sunk);
    }
    .mlabel {
        font-size: 0.78rem;
        color: var(--gre-muted);
    }
    .mval {
        font-family: var(--gre-mono);
        font-variant-numeric: tabular-nums;
        font-size: 1.15rem;
        color: var(--gre-ink);
    }
    .mval b {
        color: var(--gre-signal);
    }
    .arrow {
        color: var(--gre-muted);
        padding: 0 0.15rem;
    }
    .mhint {
        font-size: 0.72rem;
        color: var(--gre-muted);
    }
    .invariant {
        margin: 1.1rem 0 0;
        font-size: 0.85rem;
        line-height: 1.5;
        color: var(--gre-muted);
        border-left: 2px solid var(--gre-signal);
        padding-left: 0.7rem;
    }
    .invariant b {
        color: var(--gre-ink);
        font-family: var(--gre-mono);
    }
    .legend {
        display: flex;
        flex-wrap: wrap;
        gap: 0.9rem;
        margin-top: 0.9rem;
    }
    .lg {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.76rem;
        color: var(--gre-muted);
    }
    .dot {
        width: 0.7rem;
        height: 0.7rem;
        border-radius: 3px;
        display: inline-block;
    }
    .muted {
        color: var(--gre-muted);
    }
    .small {
        font-size: 0.8rem;
    }
    .err {
        color: var(--gre-abstain);
    }
    @media (max-width: 620px) {
        .metrics {
            grid-template-columns: 1fr;
        }
    }
</style>
