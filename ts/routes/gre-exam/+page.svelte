<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
Exam Mode shell — faithful to the computer-delivered GRE Math Subject Test:
one global countdown, one item at a time, five single-select options, mark +
free Back/Next, a review screen, no calculator, no pause, auto-submit at 0:00,
and no per-item feedback (results only after submit). Answers are scored
server-side (the client never receives the keys during the exam).
-->
<script lang="ts">
    import { onDestroy } from "svelte";

    import "../gre-dashboard/tokens.css";
    import Countdown from "./Countdown.svelte";
    import ItemView from "./ItemView.svelte";
    import Navigator from "./Navigator.svelte";
    import Results from "./Results.svelte";
    import { tally } from "./lib";

    const PRESETS = [
        { id: "full", label: "Full length", items: 66, time: "2h50m" },
        { id: "half", label: "Half", items: 33, time: "~1h25m" },
        { id: "third", label: "Third", items: 22, time: "~57m" },
        { id: "mini", label: "Mini", items: 11, time: "~28m" },
    ];

    let phase = $state<"setup" | "loading" | "exam" | "review" | "results" | "error">(
        "setup",
    );
    let error = $state("");
    let form = $state<any[]>([]);
    let seed = $state(0);
    let preset = $state("mini");
    let idx = $state(0);
    let answers = $state<Record<string, number>>({});
    let marked = $state<string[]>([]);
    let secondsLeft = $state(0);
    let result = $state<any>(null);
    let showHelp = $state(false);

    let timerId: ReturnType<typeof setInterval> | null = null;

    const current = $derived(form[idx]);
    const counts = $derived(tally(form.length, answers, marked));

    function stopTimer() {
        if (timerId !== null) {
            clearInterval(timerId);
            timerId = null;
        }
    }
    onDestroy(stopTimer);

    function startTimer() {
        stopTimer();
        timerId = setInterval(() => {
            secondsLeft -= 1;
            if (secondsLeft <= 0) {
                secondsLeft = 0;
                submit(); // auto-submit at 0:00, no pause
            }
        }, 1000);
    }

    async function post(endpoint: string, body: unknown): Promise<any> {
        const resp = await fetch(`/_anki/${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        return resp.json();
    }

    async function startExam(chosenPreset: string) {
        preset = chosenPreset;
        phase = "loading";
        try {
            const data = await post("greExamForm", { preset });
            if (data.locked) {
                error = data.reason || "Exam Mode is locked.";
                phase = "error";
                return;
            }
            form = data.items;
            seed = data.seed;
            secondsLeft = data.seconds;
            idx = 0;
            answers = {};
            marked = [];
            phase = "exam";
            startTimer();
        } catch (e) {
            error = String(e);
            phase = "error";
        }
    }

    function select(optionIndex: number) {
        answers = { ...answers, [current.id]: optionIndex };
    }
    function toggleMark() {
        const id = current.id;
        marked = marked.includes(id) ? marked.filter((x) => x !== id) : [...marked, id];
    }
    function goPrev() {
        idx = Math.max(0, idx - 1);
    }
    function goNext() {
        idx = Math.min(form.length - 1, idx + 1);
    }
    function jump(i: number) {
        idx = i;
        phase = "exam";
    }

    async function submit() {
        stopTimer();
        phase = "loading";
        try {
            result = await post("greExamSubmit", { preset, seed, answers });
            phase = "results";
        } catch (e) {
            error = String(e);
            phase = "error";
        }
    }

    function confirmExit() {
        if (confirm("Exit this mock? Your progress will be discarded.")) {
            stopTimer();
            phase = "setup";
        }
    }
</script>

<div class="exam">
    {#if phase === "setup"}
        <header class="masthead">
            <span class="eyebrow">GRE · Mathematics Subject Test</span>
            <h1>Exam Mode</h1>
        </header>
        <p class="lede">
            A faithful, timed mock: five options, one global clock, mark &amp; review,
            no calculator, no pause — auto-submits at zero. Every form is
            blueprint-matched (≈50% calculus / 25% algebra / 25% additional) and drawn
            only from the held-out item bank.
        </p>
        <div class="presets">
            {#each PRESETS as p}
                <button type="button" class="preset" onclick={() => startExam(p.id)}>
                    <span class="p-label">{p.label}</span>
                    <span class="p-meta">{p.items} items · {p.time}</span>
                </button>
            {/each}
        </div>
    {:else if phase === "loading"}
        <div class="notice">Preparing…</div>
    {:else if phase === "error"}
        <div class="notice err">{error}</div>
        <button type="button" class="ghost" onclick={() => (phase = "setup")}>
            Back
        </button>
    {:else if phase === "results"}
        <Results {result} />
        <button type="button" class="ghost" onclick={() => (phase = "setup")}>
            New mock
        </button>
    {:else}
        <!-- exam + review share the header/footer chrome -->
        <header class="bar">
            <span class="title">GRE Math · Exam Mode</span>
            {#if phase === "exam"}
                <span class="counter">Question {idx + 1} of {form.length}</span>
            {:else}
                <span class="counter">Review</span>
            {/if}
            <Countdown {secondsLeft} />
        </header>

        <main class="stage">
            {#if phase === "exam"}
                <ItemView
                    number={idx + 1}
                    item={current}
                    chosen={answers[current.id] ?? null}
                    onselect={select}
                />
            {:else}
                <div class="review-head">
                    <p>
                        {counts.answered} answered · {counts.unanswered} unanswered · {counts.marked}
                        marked
                    </p>
                </div>
                <Navigator {form} {answers} {marked} current={idx} onjump={jump} />
            {/if}
        </main>

        <footer class="controls">
            {#if phase === "exam"}
                <button
                    type="button"
                    class="ctl"
                    class:on={marked.includes(current.id)}
                    onclick={toggleMark}
                >
                    {marked.includes(current.id) ? "Marked" : "Mark"}
                </button>
                <button type="button" class="ctl" onclick={goPrev} disabled={idx === 0}>
                    Back
                </button>
                <button
                    type="button"
                    class="ctl"
                    onclick={goNext}
                    disabled={idx === form.length - 1}
                >
                    Next
                </button>
                <span class="spacer"></span>
                <button type="button" class="ctl" onclick={() => (phase = "review")}>
                    Review
                </button>
                <button
                    type="button"
                    class="ctl"
                    onclick={() => (showHelp = !showHelp)}
                >
                    Help
                </button>
                <button type="button" class="ctl danger" onclick={confirmExit}>
                    Exit
                </button>
            {:else}
                <button type="button" class="ctl" onclick={() => (phase = "exam")}>
                    Back to questions
                </button>
                <span class="spacer"></span>
                <button type="button" class="ctl primary" onclick={submit}>
                    Submit exam
                </button>
            {/if}
        </footer>

        {#if showHelp}
            <div class="help">
                <p><strong>How this mock works</strong></p>
                <ul>
                    <li>One global clock — no pause; the exam auto-submits at 0:00.</li>
                    <li>
                        Five options (A–E), one answer each; rights-only scoring (no
                        penalty).
                    </li>
                    <li>
                        Mark a question and use Review to jump around; change answers
                        any time.
                    </li>
                    <li>
                        No on-screen calculator — matching the real Math Subject Test.
                    </li>
                    <li>No feedback until you submit.</li>
                </ul>
                <button type="button" class="ghost" onclick={() => (showHelp = false)}>
                    Close
                </button>
            </div>
        {/if}
    {/if}
</div>

<style>
    :global(body) {
        background: var(--gre-surface-sunk);
    }
    .exam {
        max-width: 900px;
        margin: 0 auto;
        padding: 1.25rem 1.5rem 3rem;
        font-family: var(--gre-sans);
        color: var(--gre-ink);
    }
    .masthead {
        border-bottom: 2px solid var(--gre-ink);
        padding-bottom: 1rem;
        margin-bottom: 1.25rem;
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
        letter-spacing: -0.02em;
    }
    .lede {
        color: var(--gre-muted);
        max-width: 620px;
        line-height: 1.5;
    }
    .presets {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 0.8rem;
        margin-top: 1.5rem;
    }
    .preset {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
        padding: 1rem;
        border: 1px solid var(--gre-hairline);
        border-radius: var(--gre-radius);
        background: var(--gre-surface);
        cursor: pointer;
        text-align: left;
    }
    .preset:hover {
        border-color: var(--gre-signal);
    }
    .p-label {
        font-weight: 600;
        font-size: 1.05rem;
    }
    .p-meta {
        font-family: var(--gre-mono);
        font-size: 0.8rem;
        color: var(--gre-muted);
    }
    .bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding-bottom: 0.9rem;
        margin-bottom: 1.4rem;
        border-bottom: 1px solid var(--gre-hairline);
    }
    .title {
        font-family: var(--gre-mono);
        font-size: 0.8rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--gre-muted);
    }
    .counter {
        font-family: var(--gre-mono);
        font-variant-numeric: tabular-nums;
        color: var(--gre-ink);
    }
    .stage {
        min-height: 320px;
    }
    .review-head {
        color: var(--gre-muted);
        font-family: var(--gre-mono);
        font-size: 0.85rem;
        margin-bottom: 1rem;
    }
    .controls {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid var(--gre-hairline);
    }
    .spacer {
        flex: 1;
    }
    .ctl {
        padding: 0.5rem 0.9rem;
        border: 1px solid var(--gre-hairline);
        border-radius: 7px;
        background: var(--gre-surface);
        color: var(--gre-ink);
        cursor: pointer;
        font-size: 0.9rem;
    }
    .ctl:hover:not(:disabled) {
        border-color: var(--gre-signal);
    }
    .ctl:disabled {
        opacity: 0.45;
        cursor: default;
    }
    .ctl.on {
        border-color: var(--gre-abstain);
        color: var(--gre-abstain);
    }
    .ctl.primary {
        background: var(--gre-signal);
        border-color: var(--gre-signal);
        color: #fff;
        font-weight: 600;
    }
    .ctl.danger:hover {
        border-color: var(--gre-abstain);
        color: var(--gre-abstain);
    }
    .notice {
        padding: 2rem 0;
        color: var(--gre-muted);
    }
    .notice.err {
        color: var(--gre-abstain);
    }
    .ghost {
        margin-top: 1rem;
        padding: 0.45rem 0.9rem;
        border: 1px solid var(--gre-hairline);
        border-radius: 7px;
        background: transparent;
        color: var(--gre-ink);
        cursor: pointer;
    }
    .help {
        margin-top: 1.25rem;
        padding: 1rem 1.25rem;
        border: 1px solid var(--gre-hairline);
        border-radius: var(--gre-radius);
        background: var(--gre-surface);
        font-size: 0.9rem;
    }
    .help ul {
        margin: 0.5rem 0 0.75rem;
        padding-left: 1.1rem;
        color: var(--gre-muted);
        line-height: 1.6;
    }
    @media (prefers-reduced-motion: reduce) {
        .preset,
        .ctl {
            transition: none;
        }
    }
</style>
