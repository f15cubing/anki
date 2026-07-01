<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    const { memory, generatedAt }: { memory: any; generatedAt: string } = $props();
    const pct = (x: number) => `${Math.round(x * 100)}%`;
    const h = $derived(memory.headline);
</script>

<section class="memory">
    <h2>Memory</h2>
    {#if !h}
        <p class="muted">No graded reviews yet — insufficient evidence for a memory score.</p>
    {:else}
        <p class="headline">
            You can reliably recall <strong>~{pct(h.point)}</strong> of what you've studied
            <span class="range">(95% CI {pct(h.low)}–{pct(h.high)})</span>
        </p>
        {#if h.buckets_reflected < h.buckets_total}
            <p class="muted">Headline reflects {h.buckets_reflected}/{h.buckets_total} buckets.</p>
        {/if}
        <ul class="buckets">
            {#each memory.buckets as b}
                <li>
                    <span class="name">{b.bucket}</span>
                    <span class="w">({pct(b.weight)} of exam)</span>
                    {#if b.reviewed > 0}
                        {pct(b.point)} <span class="range">({pct(b.low)}–{pct(b.high)})</span>
                        · mean R {b.mean_r?.toFixed(2) ?? "—"} · n={b.reviewed}
                    {:else}
                        <span class="muted">not studied yet</span>
                    {/if}
                </li>
            {/each}
        </ul>
    {/if}
    <p class="muted note">
        Aggregate-calibrated (population FSRS defaults), not personalized. Updated {generatedAt}.
    </p>
</section>

<style>
    .memory { border: 1px solid var(--border, #ccc); border-radius: 8px; padding: 1rem; }
    .headline { font-size: 1.1rem; }
    .range { color: var(--fg-subtle, #666); }
    .muted { color: var(--fg-subtle, #888); }
    .buckets { list-style: none; padding: 0; }
    .buckets li { padding: 0.25rem 0; }
    .note { font-size: 0.85rem; margin-top: 0.75rem; }
</style>
