<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
GRE Home — the friendly landing page (Tools ▸ GRE Home; auto-opens on startup).

Reads the composed, read-only `greHomeData` payload (the same three separated scores
as the dashboard + study stats + the next-best studyable topic, plus the Exam-Mode
lock state). Imperative actions go over the webview bridge (`pycmd`) to the GreHome
dialog. Honesty rules are inherited from the shared view-model + ScoreSlot: the three
scores stay separate, Readiness is never a bare number, Performance is an observed
range or an honest "not available".
-->
<script lang="ts">
    import { onMount } from "svelte";

    import { bridgeCommand } from "@tslib/bridgecommand";

    import "../gre-dashboard/fonts.css";
    import "../gre-dashboard/tokens.css";
    import CalibrationStrip from "../gre-dashboard/CalibrationStrip.svelte";
    import ScoreSlot from "../gre-dashboard/ScoreSlot.svelte";

    let data: any = $state(null);
    let error: string | null = $state(null);
    let startupOn = $state(true);

    onMount(async () => {
        try {
            const resp = await fetch("/_anki/greHomeData", {
                method: "POST",
                headers: { "Content-Type": "application/binary" },
                body: new Uint8Array(),
            });
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            data = await resp.json();
            startupOn = !!data.show_on_startup;
        } catch (e) {
            error = String(e);
        }
    });

    const vm = $derived(data?.dashboard ?? null);
    const exam = $derived(data?.exam ?? null);
    const stats = $derived(vm?.stats ?? null);
    const next = $derived(vm?.study_next ?? null);

    const pct = (x: number) => `${Math.round((x ?? 0) * 100)}%`;

    const readinessBody = (r: any): string =>
        `Not enough evidence yet to project a score — you've studied ${Math.round(
            (r?.studied_pct ?? 0) * 100,
        )}% of the exam's topics. Abstaining honestly is the correct output.`;

    function toggleStartup(e: Event) {
        startupOn = (e.currentTarget as HTMLInputElement).checked;
        bridgeCommand(startupOn ? "gre:startup:on" : "gre:startup:off");
    }
</script>

<div class="gre-home">
    <header class="masthead">
        <div class="titles">
            <span class="eyebrow">GRE · Mathematics Subject Test</span>
            <h1>Home</h1>
        </div>
    </header>

    {#if error}
        <div class="notice err">
            Couldn't load your home — {error}. Reopen it from Tools ▸ GRE Home.
        </div>
    {:else if !vm}
        <div class="notice">Loading…</div>
    {:else}
        <!-- Primary action: go study the single best next topic. -->
        <section class="cta" class:disabled={!next}>
            {#if next}
                <button
                    type="button"
                    class="go"
                    onclick={() => bridgeCommand("gre:study")}
                >
                    <span class="go-eyebrow">Study next</span>
                    <span class="go-topic">{next.label}</span>
                    <span class="go-reason">{next.reason}</span>
                </button>
            {:else}
                <div class="go empty">
                    <span class="go-eyebrow">Study next</span>
                    <span class="go-topic">No cards yet</span>
                    <span class="go-reason">
                        Import the GRE deck to start studying.
                    </span>
                </div>
            {/if}
        </section>

        <!-- The three scores — kept strictly separate, each honest. -->
        <section class="slots" aria-label="Your three scores, kept separate">
            <section class="card memory">
                <div class="head">
                    <span class="title">Memory</span>
                    <span class="badge">Recall</span>
                </div>
                {#if vm.memory.headline}
                    <CalibrationStrip
                        point={vm.memory.headline.point}
                        low={vm.memory.headline.low}
                        high={vm.memory.headline.high}
                        n={stats?.cards_reviewed ?? null}
                        method="Wilson"
                    />
                    <p class="body">
                        You can reliably recall about
                        <strong>{pct(vm.memory.headline.point)}</strong>
                        of what you've studied.
                    </p>
                {:else}
                    <p class="body muted">
                        No graded reviews yet — study a few cards and it fills in.
                    </p>
                {/if}
            </section>

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

        <!-- Study stats: what you've reviewed. -->
        {#if stats}
            <section class="card stats">
                <div class="eyebrow">Your progress</div>
                <div class="figures">
                    <div class="figure">
                        <span class="fig-num">{stats.cards_reviewed}</span>
                        <span class="fig-lab">
                            cards reviewed
                            <span class="fig-sub">of {stats.cards_total}</span>
                        </span>
                    </div>
                    <div class="figure">
                        <span class="fig-num">
                            {stats.topics_covered}
                            <span class="fig-den">/{stats.topics_total}</span>
                        </span>
                        <span class="fig-lab">
                            topics covered
                            <span class="fig-sub">{pct(stats.studied_pct)}</span>
                        </span>
                    </div>
                    <div class="figure">
                        <span class="fig-num">{stats.exam_questions_answered}</span>
                        <span class="fig-lab">
                            exam questions answered
                            <span class="fig-sub">timed mode</span>
                        </span>
                    </div>
                </div>
                <div class="buckets">
                    {#each stats.by_bucket as b}
                        <div class="bucket">
                            <span class="b-name">{b.bucket}</span>
                            <div class="b-bar">
                                <div
                                    class="b-fill"
                                    style="width:{b.total
                                        ? Math.round((b.reviewed / b.total) * 100)
                                        : 0}%"
                                ></div>
                            </div>
                            <span class="b-count">{b.reviewed}/{b.total}</span>
                        </div>
                    {/each}
                </div>
            </section>
        {/if}

        <!-- Quick links out to the deeper surfaces. -->
        <section class="links">
            <button
                type="button"
                class="link"
                onclick={() => bridgeCommand("gre:dashboard")}
            >
                <span class="l-title">Full dashboard</span>
                <span class="l-sub">Every score, coverage map & evidence</span>
            </button>

            <button
                type="button"
                class="link"
                class:locked={exam && !exam.unlocked}
                onclick={() => bridgeCommand("gre:exam")}
            >
                <span class="l-title">
                    {#if exam && !exam.unlocked}🔒
                    {/if}Exam Mode
                </span>
                <span class="l-sub">
                    {#if !exam}
                        Timed GRE mock
                    {:else if exam.unlocked}
                        Timed, blueprint-matched mock
                    {:else}
                        Unlocks at {pct(exam.threshold)} coverage — you're at {pct(
                            exam.pct,
                        )} ({exam.studied}/{exam.total})
                    {/if}
                </span>
            </button>

            <button
                type="button"
                class="link"
                onclick={() => bridgeCommand("gre:method")}
            >
                <span class="l-title">How this differs from FSRS</span>
                <span class="l-sub">The interleaving study feature, live</span>
            </button>
        </section>

        <footer class="foot">
            <label class="startup">
                <input type="checkbox" checked={startupOn} onchange={toggleStartup} />
                Show this Home on startup
            </label>
        </footer>
    {/if}
</div>

<style>
    :global(body) {
        background: var(--gre-canvas);
    }
    .gre-home {
        max-width: 940px;
        margin: 0 auto;
        padding: 1.5rem 1.75rem 3rem;
        font-family: var(--gre-sans);
        color: var(--gre-ink);
        display: flex;
        flex-direction: column;
        gap: 1.1rem;
    }
    .masthead {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1rem;
        padding-bottom: 1.1rem;
        border-bottom: 1px solid var(--gre-hairline);
    }
    .eyebrow {
        font-family: var(--gre-mono);
        font-size: var(--gre-fs-eyebrow);
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--gre-muted);
    }
    h1 {
        margin: 0.2rem 0 0;
        font-family: var(--gre-mono);
        font-size: var(--gre-fs-title);
        font-weight: 700;
        letter-spacing: -0.03em;
        line-height: 1;
    }

    /* Primary CTA */
    .cta .go {
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        text-align: left;
        padding: 1.15rem 1.3rem;
        border: 1px solid var(--gre-signal);
        border-left: 4px solid var(--gre-signal);
        border-radius: var(--gre-radius);
        background: var(--gre-surface);
        color: var(--gre-ink);
        cursor: pointer;
        transition: box-shadow 0.15s ease;
    }
    .cta .go:hover {
        box-shadow: 0 0 0 1px var(--gre-signal);
    }
    .cta .go.empty {
        border-color: var(--gre-hairline);
        border-left-color: var(--gre-hairline);
        cursor: default;
    }
    .go-eyebrow {
        font-family: var(--gre-mono);
        font-size: var(--gre-fs-eyebrow);
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--gre-signal);
    }
    .go-topic {
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: -0.01em;
    }
    .go-reason {
        color: var(--gre-muted);
        font-size: var(--gre-fs-body);
    }

    .slots {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
    }
    .card {
        background: var(--gre-surface);
        border: 1px solid var(--gre-hairline);
        border-radius: var(--gre-radius);
        padding: 1.1rem 1.15rem;
    }
    .card.memory {
        display: flex;
        flex-direction: column;
        gap: 0.55rem;
        border-left: 3px solid var(--gre-signal);
    }
    .head {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 0.5rem;
    }
    .title {
        font-family: var(--gre-mono);
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--gre-ink);
    }
    .badge {
        font-family: var(--gre-mono);
        font-size: 0.68rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--gre-signal);
        white-space: nowrap;
    }
    .body {
        margin: 0;
        font-size: var(--gre-fs-body);
        color: var(--gre-ink);
        line-height: 1.4;
    }
    .body strong {
        color: var(--gre-signal);
        font-weight: 700;
    }
    .body.muted {
        color: var(--gre-muted);
    }

    /* Stats */
    .stats .eyebrow {
        margin-bottom: 0.85rem;
    }
    .figures {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
    }
    .figure {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }
    .fig-num {
        font-family: var(--gre-mono);
        font-variant-numeric: tabular-nums;
        font-size: 2.6rem;
        font-weight: 700;
        color: var(--gre-ink);
        line-height: 1;
    }
    .fig-den {
        color: var(--gre-muted);
        font-size: 1.6rem;
        font-weight: 400;
    }
    .fig-lab {
        font-size: 0.82rem;
        color: var(--gre-muted);
        line-height: 1.3;
    }
    .fig-sub {
        display: block;
        font-family: var(--gre-mono);
        font-size: 0.72rem;
        color: var(--gre-faint);
    }
    .buckets {
        margin-top: 1.1rem;
        padding-top: 0.95rem;
        border-top: 1px solid var(--gre-hairline);
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .bucket {
        display: grid;
        grid-template-columns: 5.5rem 1fr 3rem;
        align-items: center;
        gap: 0.6rem;
    }
    .b-name {
        font-size: 0.82rem;
        color: var(--gre-ink);
        text-transform: capitalize;
    }
    .b-bar {
        height: 7px;
        border-radius: 999px;
        background: var(--gre-surface-sunk);
        border: 1px solid var(--gre-hairline);
        overflow: hidden;
    }
    .b-fill {
        height: 100%;
        background: var(--gre-band);
        border-right: 2px solid var(--gre-signal);
    }
    .b-count {
        font-family: var(--gre-mono);
        font-variant-numeric: tabular-nums;
        font-size: 0.75rem;
        color: var(--gre-muted);
        text-align: right;
    }

    /* Quick links */
    .links {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
    }
    .link {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
        text-align: left;
        padding: 0.95rem 1.05rem;
        border: 1px solid var(--gre-hairline);
        border-radius: var(--gre-radius);
        background: var(--gre-surface);
        color: var(--gre-ink);
        cursor: pointer;
        transition: border-color 0.15s ease;
    }
    .link:hover {
        border-color: var(--gre-signal);
    }
    .link.locked {
        border-style: dashed;
    }
    .link.locked:hover {
        border-color: var(--gre-abstain);
    }
    .l-title {
        font-weight: 600;
        font-size: 0.98rem;
    }
    .l-sub {
        font-size: 0.8rem;
        color: var(--gre-muted);
        line-height: 1.35;
    }

    .foot {
        margin-top: 0.4rem;
    }
    .startup {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.82rem;
        color: var(--gre-muted);
        cursor: pointer;
    }

    .notice {
        color: var(--gre-muted);
        padding: 2rem 0;
    }
    .notice.err {
        color: var(--gre-abstain);
    }

    @media (max-width: 720px) {
        .slots,
        .figures,
        .links {
            grid-template-columns: 1fr;
        }
    }
</style>
