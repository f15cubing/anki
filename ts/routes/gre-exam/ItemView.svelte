<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
One item on screen at a time (faithful to the exam): the stem + five
single-select options A–E. No per-item feedback — correctness is only revealed
after the whole form is submitted. Math is shown as monospace ASCII (the source
items are plain expressions, not LaTeX).
-->
<script lang="ts">
    import { OPTION_LETTERS } from "./lib";

    interface Props {
        number: number;
        item: { question: string; options: string[] };
        chosen: number | null;
        onselect: (index: number) => void;
    }
    const { number, item, chosen, onselect }: Props = $props();
</script>

<div class="item">
    <p class="stem">
        <span class="num">{number}.</span>
        <span class="q">{item.question}</span>
    </p>
    <div class="options" role="radiogroup" aria-label={`Question ${number} options`}>
        {#each item.options as option, i}
            <button
                type="button"
                class="option"
                class:selected={chosen === i}
                role="radio"
                aria-checked={chosen === i}
                onclick={() => onselect(i)}
            >
                <span class="letter">{OPTION_LETTERS[i]}</span>
                <span class="text">{option}</span>
            </button>
        {/each}
    </div>
</div>

<style>
    .item {
        max-width: 720px;
    }
    .stem {
        font-size: 1.1rem;
        line-height: 1.5;
        color: var(--gre-ink);
        margin: 0 0 1.4rem;
    }
    .num {
        font-family: var(--gre-mono);
        font-weight: 600;
        color: var(--gre-muted);
        margin-right: 0.35rem;
    }
    .q {
        font-family: var(--gre-mono);
    }
    .options {
        display: flex;
        flex-direction: column;
        gap: 0.55rem;
    }
    .option {
        display: flex;
        align-items: baseline;
        gap: 0.75rem;
        text-align: left;
        padding: 0.7rem 0.9rem;
        border: 1px solid var(--gre-hairline);
        border-radius: 8px;
        background: var(--gre-surface);
        color: var(--gre-ink);
        cursor: pointer;
        font-size: 1rem;
        transition:
            border-color 0.12s ease,
            background 0.12s ease;
    }
    .option:hover {
        border-color: var(--gre-signal);
    }
    .option.selected {
        border-color: var(--gre-signal);
        box-shadow: inset 0 0 0 1px var(--gre-signal);
    }
    .letter {
        font-family: var(--gre-mono);
        font-weight: 600;
        color: var(--gre-signal);
        min-width: 1.2rem;
    }
    .text {
        font-family: var(--gre-mono);
        font-variant-numeric: tabular-nums;
    }
    .option:focus-visible {
        outline: 2px solid var(--gre-signal);
        outline-offset: 2px;
    }
    @media (prefers-reduced-motion: reduce) {
        .option {
            transition: none;
        }
    }
</style>
