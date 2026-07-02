<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import CalibrationStrip from "./CalibrationStrip.svelte";

    const { memory }: { memory: any } = $props();
    const h = $derived(memory.headline);
    const pct = (x: number) => `${Math.round(x * 100)}%`;
    const totalReviewed = $derived(
        (memory.buckets ?? []).reduce(
            (sum: number, b: any) => sum + (b.reviewed ?? 0),
            0,
        ),
    );
</script>

<section class="memory">
    <div class="eyebrow">Memory · what you can recall now</div>

    {#if !h}
        <p class="empty">
            No graded reviews yet — insufficient evidence for a memory score. Study a
            few cards and reopen this dashboard.
        </p>
    {:else}
        <p class="lede">
            You can reliably recall about <strong>{pct(h.point)}</strong>
            of what you've studied.
        </p>
        <CalibrationStrip point={h.point} low={h.low} high={h.high} n={totalReviewed} />
        {#if h.buckets_reflected < h.buckets_total}
            <p class="caveat">
                Headline reflects {h.buckets_reflected} of {h.buckets_total} exam areas —
                the rest have no graded reviews yet.
            </p>
        {/if}

        <div class="buckets">
            {#each memory.buckets as b}
                <div class="bucket">
                    <CalibrationStrip
                        label={`${b.bucket} · ${pct(b.weight)} of exam`}
                        point={b.reviewed > 0 ? b.point : null}
                        low={b.reviewed > 0 ? b.low : null}
                        high={b.reviewed > 0 ? b.high : null}
                        n={b.reviewed > 0 ? b.reviewed : null}
                        compact
                    />
                    {#if b.reviewed > 0 && b.mean_r != null}
                        <span class="meanr">mean recall {b.mean_r.toFixed(2)}</span>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}

    <p class="foot">
        Aggregate-calibrated on population FSRS defaults — not a personalized model.
        Areas are weighted 50 / 25 / 25 (calculus / algebra / additional) to match the
        exam.
    </p>
</section>

<style>
    .memory {
        background: var(--gre-surface);
        border: 1px solid var(--gre-hairline);
        border-radius: var(--gre-radius);
        padding: 1.25rem 1.35rem;
    }
    .eyebrow {
        font-family: var(--gre-mono);
        font-size: var(--gre-fs-eyebrow);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--gre-muted);
        margin-bottom: 0.75rem;
    }
    .lede {
        font-size: var(--gre-fs-headline);
        line-height: 1.3;
        color: var(--gre-ink);
        margin: 0 0 0.75rem;
    }
    .lede strong {
        color: var(--gre-signal);
        font-weight: 700;
    }
    .empty {
        color: var(--gre-muted);
        font-size: var(--gre-fs-body);
    }
    .caveat {
        color: var(--gre-muted);
        font-size: 0.82rem;
        margin: 0.6rem 0 0;
    }
    .buckets {
        display: flex;
        flex-direction: column;
        gap: 0.9rem;
        margin-top: 1.2rem;
        padding-top: 1.1rem;
        border-top: 1px solid var(--gre-hairline);
    }
    .bucket {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
    }
    .bucket :global(.label) {
        text-transform: capitalize;
    }
    .meanr {
        font-family: var(--gre-mono);
        font-variant-numeric: tabular-nums;
        font-size: 0.78rem;
        color: var(--gre-muted);
    }
    .foot {
        margin: 1.2rem 0 0;
        font-size: 0.78rem;
        color: var(--gre-muted);
        line-height: 1.45;
    }
</style>
