<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import CalibrationStrip from "./CalibrationStrip.svelte";

    const { coverage, bestNext = null }: { coverage: any; bestNext?: string | null } =
        $props();
    const pct = (x: number) => `${Math.round(x * 100)}%`;
    const prettyLeaf = (leaf: string) => leaf.replace(/_/g, " ");

    const byBucket = $derived.by(() => {
        const groups: Record<string, any[]> = {};
        for (const leaf of coverage.leaves) {
            (groups[leaf.bucket] ??= []).push(leaf);
        }
        return groups;
    });
</script>

<section class="coverage">
    <div class="head">
        <div class="eyebrow">Coverage · the 17 exam leaf topics</div>
        <div class="stats">
            <span>
                <b>{pct(coverage.deck_pct)}</b>
                in deck
            </span>
            <span>
                <b>{pct(coverage.studied_pct)}</b>
                studied
            </span>
        </div>
    </div>

    {#each Object.entries(byBucket) as [bucket, leaves]}
        <h3>{bucket}</h3>
        <div class="grid">
            {#each leaves as leaf}
                <div
                    class="cell"
                    class:uncovered={!leaf.has_cards}
                    class:best={leaf.tag === bestNext}
                >
                    <span class="name">{prettyLeaf(leaf.leaf)}</span>
                    {#if leaf.studied && leaf.memory}
                        <CalibrationStrip
                            point={leaf.memory.point}
                            low={leaf.memory.low}
                            high={leaf.memory.high}
                            n={leaf.memory.reviewed}
                            compact
                        />
                    {:else}
                        <CalibrationStrip
                            point={null}
                            compact
                            emptyLabel={leaf.has_cards ? "not studied" : "no cards"}
                        />
                    {/if}
                </div>
            {/each}
        </div>
    {/each}
</section>

<style>
    .coverage {
        background: var(--gre-surface);
        border: 1px solid var(--gre-hairline);
        border-radius: var(--gre-radius);
        padding: 1.25rem 1.35rem;
    }
    .head {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 0.5rem;
    }
    .eyebrow {
        font-family: var(--gre-mono);
        font-size: var(--gre-fs-eyebrow);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--gre-muted);
    }
    .stats {
        display: flex;
        gap: 1rem;
        font-family: var(--gre-mono);
        font-variant-numeric: tabular-nums;
        font-size: 0.82rem;
        color: var(--gre-muted);
    }
    .stats b {
        color: var(--gre-ink);
    }
    h3 {
        text-transform: capitalize;
        font-size: 0.9rem;
        color: var(--gre-ink);
        margin: 1.1rem 0 0.55rem;
    }
    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
        gap: 0.6rem;
    }
    .cell {
        border: 1px solid var(--gre-hairline);
        border-radius: 8px;
        padding: 0.55rem 0.65rem;
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
        background: var(--gre-surface);
    }
    .cell.uncovered {
        opacity: 0.6;
    }
    /* The single best-next topic gets a quiet ring — the one place the eye is led. */
    .cell.best {
        border-color: var(--gre-signal);
        box-shadow: 0 0 0 1px var(--gre-signal);
    }
    .name {
        font-weight: 600;
        font-size: 0.84rem;
        color: var(--gre-ink);
        text-transform: capitalize;
    }
</style>
