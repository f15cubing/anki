<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import { onMount } from "svelte";

    import "./tokens.css";
    import CoverageMap from "./CoverageMap.svelte";
    import MemoryPanel from "./MemoryPanel.svelte";
    import ScoreSlot from "./ScoreSlot.svelte";

    let vm: any = $state(null);
    let error: string | null = $state(null);

    onMount(async () => {
        try {
            const resp = await fetch("/_anki/greDashboardData", {
                method: "POST",
                headers: { "Content-Type": "application/binary" },
                body: new Uint8Array(),
            });
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            vm = await resp.json();
        } catch (e) {
            error = String(e);
        }
    });

    function formatStamp(iso: string): string {
        const d = new Date(iso);
        return isNaN(d.getTime())
            ? iso
            : d.toLocaleString(undefined, {
                  dateStyle: "medium",
                  timeStyle: "short",
              });
    }

    const readinessBody = (r: any): string =>
        `Insufficient evidence to score a projected exam result — you've studied ${Math.round(
            r.studied_pct * 100,
        )}% of the exam's topics. That's the honest output, not a gap to paper over.`;
</script>

<div class="gre-dashboard">
    <header class="masthead">
        <div class="titles">
            <span class="eyebrow">GRE · Mathematics Subject Test</span>
            <h1>Readiness</h1>
        </div>
        {#if vm}
            <span class="updated">updated {formatStamp(vm.generated_at)}</span>
        {/if}
    </header>

    {#if error}
        <div class="notice error">
            Couldn't load the dashboard — {error}. Close and reopen it from Tools ▸ GRE
            readiness.
        </div>
    {:else if !vm}
        <div class="notice">Loading…</div>
    {:else}
        <div class="stack">
            <MemoryPanel memory={vm.memory} />

            <section
                class="slots"
                aria-label="Performance and Readiness, kept separate from Memory"
            >
                <ScoreSlot
                    title="Performance"
                    state={vm.performance.state}
                    body={vm.performance.note}
                    point={vm.performance.point ?? null}
                    low={vm.performance.low ?? null}
                    high={vm.performance.high ?? null}
                    n={vm.performance.total ?? null}
                />
                <ScoreSlot
                    title="Readiness"
                    state={vm.readiness.state}
                    body={readinessBody(vm.readiness)}
                    bestNext={vm.readiness.next_best_topic}
                    reasons={vm.readiness.reasons}
                />
            </section>

            <CoverageMap
                coverage={vm.coverage}
                bestNext={vm.readiness.next_best_topic}
            />
        </div>
    {/if}
</div>

<style>
    :global(body) {
        background: var(--gre-surface-sunk);
    }
    .gre-dashboard {
        max-width: 940px;
        margin: 0 auto;
        padding: 1.5rem 1.75rem 3rem;
        font-family: var(--gre-sans);
        color: var(--gre-ink);
    }
    .masthead {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1rem;
        padding-bottom: 1.1rem;
        margin-bottom: 1.4rem;
        border-bottom: 2px solid var(--gre-ink);
    }
    .eyebrow {
        font-family: var(--gre-mono);
        font-size: var(--gre-fs-eyebrow);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--gre-signal);
    }
    h1 {
        margin: 0.15rem 0 0;
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        line-height: 1;
    }
    .updated {
        font-family: var(--gre-mono);
        font-variant-numeric: tabular-nums;
        font-size: 0.75rem;
        color: var(--gre-muted);
        white-space: nowrap;
    }
    .stack {
        display: flex;
        flex-direction: column;
        gap: 1.1rem;
    }
    .slots {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.1rem;
    }
    .notice {
        color: var(--gre-muted);
        padding: 2rem 0;
    }
    .notice.error {
        color: var(--gre-abstain);
    }

    /* one restrained page-load reveal; disabled for reduced motion */
    .stack > :global(*) {
        animation: gre-rise 0.28s ease both;
    }
    .stack > :global(*:nth-child(2)) {
        animation-delay: 0.06s;
    }
    .stack > :global(*:nth-child(3)) {
        animation-delay: 0.12s;
    }
    @keyframes gre-rise {
        from {
            opacity: 0;
            transform: translateY(6px);
        }
        to {
            opacity: 1;
            transform: none;
        }
    }
    @media (prefers-reduced-motion: reduce) {
        .stack > :global(*) {
            animation: none;
        }
    }
    @media (max-width: 620px) {
        .slots {
            grid-template-columns: 1fr;
        }
    }
</style>
