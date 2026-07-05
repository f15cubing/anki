<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
"How this app differs from FSRS" — a read-only explainer. FSRS schedules memory; we
keep it byte-for-byte and add layers above it (interleaving, timed mode, three
separated scores, an honesty rule). The interleaving section is interactive and runs
the real vendored algorithm; everything else is static, technical prose.
-->
<script lang="ts">
    import CalibrationStrip from "../gre-dashboard/CalibrationStrip.svelte";
    import "../gre-dashboard/tokens.css";
    import Interleave from "./Interleave.svelte";
</script>

<div class="method">
    <header class="masthead">
        <span class="eyebrow">GRE · Mathematics Subject Test · study method</span>
        <h1>
            Built on FSRS.
            <br />
            Not just FSRS.
        </h1>
        <p class="lede">
            FSRS is a memory model: it predicts when you'll forget a card and schedules
            the review. A subject exam asks more than memory. We keep FSRS's scheduling
            exactly as it is and add four layers on top — you can see each one below.
        </p>
    </header>

    <section class="sec">
        <span class="sec-eyebrow">Foundation</span>
        <h2>One question vs. three</h2>
        <div class="compare">
            <div class="col">
                <span class="col-h">FSRS answers</span>
                <p>
                    <b>Will you forget this card?</b>
                    — retrievability
                    <span class="mono">R</span>
                    , turned into a due date. It does this well, and we don't change it.
                </p>
            </div>
            <div class="col">
                <span class="col-h accent">An exam also asks</span>
                <p>
                    <b>
                        Can you answer an unseen item, under time, across mixed topics —
                        and are you ready?
                    </b>
                     None of those are scheduling questions.
                </p>
            </div>
        </div>
        <p class="aside">
            The only change we made inside Anki's engine is a <b>read-only</b>
             query that reads per-topic mastery. Everything else on this page is a layer
            above the engine — and can be switched off without touching your reviews.
        </p>
    </section>

    <section class="sec">
        <span class="sec-eyebrow">Ordering</span>
        <h2>Interleaving — mix the types FSRS would block</h2>
        <p class="body">
            FSRS orders due cards by urgency, which tends to group same-type problems
            together. We add a constrained re-sort on top: show the most-urgent card
            whose problem type differs from the last few — unless a card has waited its
            limit, in which case it goes first. Drag <span class="mono">K</span>
            and
            <span class="mono">W</span>
             to run the real algorithm on an example queue.
        </p>
        <Interleave />
        <p class="cite">
            Interleaving confusable types trains you to pick the strategy <em>
                before
            </em>
            executing it — the exact demand a GRE item makes. Rohrer et al. 2020 (classroom
            d≈0.83); Brunmair &amp; Richter 2019 (math g≈0.34). Over an app that already
            spaces, the honest incremental effect is smaller (dz≈0.2–0.35), so we ship it
            as a pre-registered pilot, not a promise.
        </p>
    </section>

    <section class="sec">
        <span class="sec-eyebrow">Conditions</span>
        <h2>Timed mode — because the exam is speeded</h2>
        <p class="body">
            FSRS has no notion of test conditions. The Math Subject Test runs at about
            <b>2.58 minutes per item</b>
            , no calculator, no pause. So we add a faithful timed mock: one global
            clock, five options, mark &amp; review, rights-only scoring, auto-submit at
            zero. The construct we preserve is
            <b>speededness</b>
            — shorter presets keep the exact pace with fewer items, not a relaxed one.
        </p>
        <p class="where">
            Open it from <b>Tools ▸ GRE exam mode</b>
            .
        </p>
    </section>

    <section class="sec">
        <span class="sec-eyebrow">Scoring</span>
        <h2>Three scores, never blended</h2>
        <p class="body">
            FSRS gives you one signal: memory. We keep three apart and always show each
            as a <b>range</b>
            , never a bare point.
        </p>
        <ul class="scores">
            <li>
                <b>Memory</b>
                 — P(recall a card now), straight from FSRS.
            </li>
            <li>
                <b>Performance</b>
                 — P(correct on an unseen, exam-style item).
            </li>
            <li>
                <b>Readiness</b>
                 — a projected 200–990 scaled score.
            </li>
        </ul>
        <div class="strip-demo" aria-hidden="true">
            <CalibrationStrip
                point={0.82}
                low={0.74}
                high={0.88}
                n={140}
                label="Memory — P(recall)"
            />
            <CalibrationStrip
                point={null}
                label="Performance — P(correct, unseen)"
                emptyLabel="no attempts yet"
            />
            <CalibrationStrip
                point={null}
                tone="abstain"
                label="Readiness — projected 200–990"
                emptyLabel="no track record yet"
            />
        </div>
        <p class="cap">
            Illustration. Three separate ranges; readiness stays blank until there's
            evidence for it. See yours in <b>Tools ▸ GRE readiness dashboard</b>
            .
        </p>
    </section>

    <section class="sec">
        <span class="sec-eyebrow">Honesty</span>
        <h2>The give-up rule</h2>
        <p class="body">
            A confident number with no evidence is the failure we most want to avoid. So
            readiness stays blank until <b>all three</b>
             hold:
        </p>
        <ul class="gates">
            <li>≥ 200 graded reviews</li>
            <li>≥ 50% of the exam's topics covered</li>
            <li>the projected range is tight enough to be useful</li>
        </ul>
        <p class="body">
            Until then you see <em>"no track record yet"</em>
             plus the single best topic to study next. At one student over one week, that
            restraint is the correct output — not a gap to paper over.
        </p>
    </section>
</div>

<style>
    :global(body) {
        background: var(--gre-surface-sunk);
    }
    .method {
        max-width: 760px;
        margin: 0 auto;
        padding: 1.75rem 1.75rem 4rem;
        font-family: var(--gre-sans);
        color: var(--gre-ink);
        line-height: 1.55;
    }
    .masthead {
        border-bottom: 2px solid var(--gre-ink);
        padding-bottom: 1.4rem;
        margin-bottom: 2rem;
    }
    .eyebrow {
        font-family: var(--gre-mono);
        font-size: var(--gre-fs-eyebrow);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--gre-signal);
    }
    h1 {
        margin: 0.3rem 0 0.75rem;
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        line-height: 1.02;
    }
    .lede {
        margin: 0;
        max-width: 60ch;
        color: var(--gre-muted);
    }
    .sec {
        margin: 2.4rem 0;
    }
    .sec-eyebrow {
        font-family: var(--gre-mono);
        font-size: var(--gre-fs-eyebrow);
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--gre-muted);
    }
    .sec h2 {
        margin: 0.35rem 0 0.9rem;
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: -0.01em;
    }
    .body,
    .where {
        margin: 0 0 0.9rem;
        max-width: 62ch;
    }
    .where {
        color: var(--gre-muted);
    }
    .compare {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    .col {
        border: 1px solid var(--gre-hairline);
        border-radius: var(--gre-radius);
        background: var(--gre-surface);
        padding: 0.9rem 1rem;
    }
    .col-h {
        font-family: var(--gre-mono);
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--gre-muted);
    }
    .col-h.accent {
        color: var(--gre-signal);
    }
    .col p {
        margin: 0.4rem 0 0;
        font-size: 0.92rem;
    }
    .aside {
        margin: 0;
        font-size: 0.85rem;
        color: var(--gre-muted);
        border-left: 2px solid var(--gre-hairline);
        padding-left: 0.75rem;
    }
    .cite {
        margin: 1rem 0 0;
        font-size: 0.8rem;
        line-height: 1.5;
        color: var(--gre-muted);
    }
    .mono {
        font-family: var(--gre-mono);
        color: var(--gre-signal);
    }
    .scores,
    .gates {
        margin: 0 0 1rem;
        padding-left: 1.1rem;
        max-width: 62ch;
    }
    .scores li,
    .gates li {
        margin: 0.3rem 0;
    }
    .strip-demo {
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
        padding: 1.1rem 1.25rem;
        border: 1px solid var(--gre-hairline);
        border-radius: var(--gre-radius);
        background: var(--gre-surface);
    }
    .cap {
        margin: 0.75rem 0 0;
        font-size: 0.8rem;
        color: var(--gre-muted);
    }
    b {
        color: var(--gre-ink);
    }

    /* one restrained page-load reveal; disabled for reduced motion */
    .sec {
        animation: gre-rise 0.3s ease both;
    }
    .sec:nth-of-type(2) {
        animation-delay: 0.05s;
    }
    .sec:nth-of-type(3) {
        animation-delay: 0.1s;
    }
    .sec:nth-of-type(4) {
        animation-delay: 0.15s;
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
        .sec {
            animation: none;
        }
    }
    @media (max-width: 620px) {
        .compare {
            grid-template-columns: 1fr;
        }
        h1 {
            font-size: 2rem;
        }
    }
</style>
