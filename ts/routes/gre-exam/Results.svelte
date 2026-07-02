<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
Post-submit results (deferred feedback — no per-item feedback during the exam).
Rights-only score as a range, per-bucket breakdown, then a full item review with
the key + explanation revealed. The score feeds Readiness downstream; it is never
blended with Memory/Performance here.
-->
<script lang="ts">
    import CalibrationStrip from "../gre-dashboard/CalibrationStrip.svelte";
    import { OPTION_LETTERS } from "./lib";

    const { result }: { result: any } = $props();
    const buckets = $derived(
        Object.entries(result.by_bucket ?? {}) as [
            string,
            { correct: number; total: number },
        ][],
    );
</script>

<div class="results">
    <h2>Results</h2>
    <p class="headline">
        You answered <strong>{result.correct}</strong>
        of {result.total} correctly — rights-only, no penalty for omissions.
    </p>
    <CalibrationStrip
        point={result.proportion.point}
        low={result.proportion.low}
        high={result.proportion.high}
        n={result.total}
    />
    <p class="note">
        This raw score feeds the <strong>Readiness</strong>
         estimate — it is not blended with your Memory or Performance scores.
    </p>

    <h3>By area</h3>
    <div class="buckets">
        {#each buckets as [bucket, b] (bucket)}
            <CalibrationStrip
                label={`${bucket} — ${b.correct}/${b.total}`}
                point={b.total > 0 ? b.correct / b.total : null}
                n={b.total}
                compact
            />
        {/each}
    </div>

    <h3>Review</h3>
    <ol class="review">
        {#each result.items as item, i (item.id)}
            <li class="ritem" class:wrong={!item.is_correct}>
                <p class="rstem">
                    <span class="rnum">{i + 1}.</span>
                    {item.question}
                </p>
                <p class="answers">
                    <span class="you" class:ok={item.is_correct}>
                        Your answer:
                        {#if item.chosen === null || item.chosen === undefined}
                            <em>omitted</em>
                        {:else}
                            {OPTION_LETTERS[item.chosen]}. {item.options[item.chosen]}
                        {/if}
                    </span>
                    {#if !item.is_correct}
                        <span class="key">
                            Correct: {OPTION_LETTERS[item.correct_index]}. {item
                                .options[item.correct_index]}
                        </span>
                    {/if}
                </p>
                {#if item.explanation}
                    <p class="explain">{item.explanation}</p>
                {/if}
            </li>
        {/each}
    </ol>
</div>

<style>
    .results {
        max-width: 760px;
    }
    h2 {
        margin: 0 0 0.75rem;
    }
    h3 {
        margin: 1.75rem 0 0.75rem;
        font-size: 0.95rem;
    }
    .headline {
        font-size: 1.15rem;
        color: var(--gre-ink);
        margin: 0 0 0.75rem;
    }
    .headline strong {
        color: var(--gre-signal);
    }
    .note {
        font-size: 0.82rem;
        color: var(--gre-muted);
        margin: 0.75rem 0 0;
    }
    .buckets {
        display: flex;
        flex-direction: column;
        gap: 0.8rem;
    }
    .buckets :global(.label) {
        text-transform: capitalize;
    }
    .review {
        list-style: none;
        padding: 0;
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 0.9rem;
    }
    .ritem {
        border: 1px solid var(--gre-hairline);
        border-left: 3px solid var(--gre-signal);
        border-radius: 8px;
        padding: 0.75rem 0.9rem;
        background: var(--gre-surface);
    }
    .ritem.wrong {
        border-left-color: var(--gre-abstain);
    }
    .rstem {
        font-family: var(--gre-mono);
        margin: 0 0 0.5rem;
        color: var(--gre-ink);
    }
    .rnum {
        color: var(--gre-muted);
    }
    .answers {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
        margin: 0;
        font-family: var(--gre-mono);
        font-size: 0.9rem;
    }
    .you {
        color: var(--gre-abstain);
    }
    .you.ok {
        color: var(--gre-signal);
    }
    .key {
        color: var(--gre-signal);
    }
    .explain {
        margin: 0.5rem 0 0;
        font-size: 0.85rem;
        color: var(--gre-muted);
    }
</style>
