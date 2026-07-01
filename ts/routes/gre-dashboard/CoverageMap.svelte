<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    const { coverage }: { coverage: any } = $props();
    const pct = (x: number) => `${Math.round(x * 100)}%`;
    const byBucket = $derived.by(() => {
        const groups: Record<string, any[]> = {};
        for (const leaf of coverage.leaves) {
            (groups[leaf.bucket] ??= []).push(leaf);
        }
        return groups;
    });
</script>

<section class="coverage">
    <h2>Coverage map</h2>
    <p class="muted">Deck coverage {pct(coverage.deck_pct)} · studied coverage {pct(coverage.studied_pct)}</p>
    {#each Object.entries(byBucket) as [bucket, leaves]}
        <h3>{bucket}</h3>
        <div class="grid">
            {#each leaves as leaf}
                <div class="cell" class:uncovered={!leaf.has_cards} class:studied={leaf.studied}>
                    <span class="leaf">{leaf.leaf}</span>
                    {#if leaf.studied && leaf.memory}
                        <span class="mem">{pct(leaf.memory.point)} ({pct(leaf.memory.low)}–{pct(leaf.memory.high)})</span>
                    {:else if leaf.has_cards}
                        <span class="muted">not studied</span>
                    {:else}
                        <span class="muted">no cards</span>
                    {/if}
                </div>
            {/each}
        </div>
    {/each}
</section>

<style>
    .coverage { margin-top: 1rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 0.5rem; }
    .cell { border: 1px solid var(--border, #ccc); border-radius: 6px; padding: 0.5rem; display: flex; flex-direction: column; }
    .cell.studied { border-color: var(--accent, #4c8bf5); }
    .cell.uncovered { opacity: 0.55; }
    .leaf { font-weight: 600; }
    .mem { color: var(--fg-subtle, #555); }
    .muted { color: var(--fg-subtle, #888); }
</style>
