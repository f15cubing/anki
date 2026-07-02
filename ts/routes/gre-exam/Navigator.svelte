<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
The review screen: a grid of every item showing answered / unanswered / marked,
click any number to jump straight to it (faithful to the exam's review screen).
-->
<script lang="ts">
    interface Props {
        form: { id: string }[];
        answers: Record<string, number | null>;
        marked: string[];
        current: number;
        onjump: (index: number) => void;
    }
    const { form, answers, marked, current, onjump }: Props = $props();
    const isAnswered = (id: string) =>
        answers[id] !== null && answers[id] !== undefined;
</script>

<div class="navigator">
    <div class="legend">
        <span>
            <i class="swatch answered"></i>
             answered
        </span>
        <span>
            <i class="swatch"></i>
             unanswered
        </span>
        <span>
            <i class="swatch marked"></i>
             marked
        </span>
    </div>
    <div class="grid">
        {#each form as item, i}
            <button
                type="button"
                class="cell"
                class:answered={isAnswered(item.id)}
                class:marked={marked.includes(item.id)}
                class:current={i === current}
                onclick={() => onjump(i)}
                aria-label={`Question ${i + 1}${isAnswered(item.id) ? ", answered" : ""}${marked.includes(item.id) ? ", marked" : ""}`}
            >
                {i + 1}
            </button>
        {/each}
    </div>
</div>

<style>
    .navigator {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }
    .legend {
        display: flex;
        gap: 1.25rem;
        font-size: 0.82rem;
        color: var(--gre-muted);
    }
    .legend span {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }
    .swatch {
        width: 0.85rem;
        height: 0.85rem;
        border-radius: 3px;
        border: 1px solid var(--gre-hairline);
        background: var(--gre-surface);
        display: inline-block;
    }
    .swatch.answered {
        background: var(--gre-band);
        border-color: var(--gre-signal);
    }
    .swatch.marked {
        border-color: var(--gre-abstain);
        border-width: 2px;
    }
    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(2.4rem, 1fr));
        gap: 0.4rem;
    }
    .cell {
        aspect-ratio: 1;
        border: 1px solid var(--gre-hairline);
        border-radius: 6px;
        background: var(--gre-surface);
        color: var(--gre-ink);
        font-family: var(--gre-mono);
        font-variant-numeric: tabular-nums;
        font-size: 0.85rem;
        cursor: pointer;
    }
    .cell.answered {
        background: var(--gre-band);
        border-color: var(--gre-signal);
    }
    .cell.marked {
        border-color: var(--gre-abstain);
        border-width: 2px;
    }
    .cell.current {
        outline: 2px solid var(--gre-signal);
        outline-offset: 1px;
    }
    .cell:focus-visible {
        outline: 2px solid var(--gre-signal);
        outline-offset: 1px;
    }
</style>
