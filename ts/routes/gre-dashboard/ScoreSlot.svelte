<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
A single score slot. Redesign owns the chrome; the scoring layer owns what goes
inside — when a score goes live it drops a CalibrationStrip (a range, never a
bare point) into the slot. The state guard keeps a fabricated number from ever
slipping in: the only states that render are the two honest give-up states and
"observed", and "observed" renders a number ONLY when a real range payload
(point + low + high) is present — otherwise it collapses to "not available".
-->
<script lang="ts">
    import CalibrationStrip from "./CalibrationStrip.svelte";

    const ALLOWED_STATES = new Set([
        "insufficient_evidence",
        "not_available",
        "observed",
    ]);
    const {
        title,
        state,
        body = "",
        reasons = [],
        bestNext = null,
        point = null,
        low = null,
        high = null,
        n = null,
    }: {
        title: string;
        state: string;
        body?: string;
        reasons?: string[];
        bestNext?: string | null;
        point?: number | null;
        low?: number | null;
        high?: number | null;
        n?: number | null;
    } = $props();

    const hasRange = $derived(
        typeof point === "number" &&
            typeof low === "number" &&
            typeof high === "number",
    );
    // "observed" only survives with a real range; anything else (incl. an
    // "observed" state missing its range, or an unknown state) falls back to
    // "not available" so a fabricated point can never slip in.
    const safeState = $derived(
        state === "observed"
            ? hasRange
                ? "observed"
                : "not_available"
            : ALLOWED_STATES.has(state)
              ? state
              : "not_available",
    );
    const badge = $derived(
        safeState === "insufficient_evidence"
            ? "Insufficient evidence"
            : safeState === "observed"
              ? "Observed"
              : "Not available yet",
    );
    const leaf = (tag: string | null) => (tag ? tag.split("::").pop() : null);
</script>

<section class="slot {safeState}">
    <div class="head">
        <span class="title">{title}</span>
        <span class="badge">{badge}</span>
    </div>

    {#if safeState === "observed"}
        <CalibrationStrip {point} {low} {high} {n} scale="pct" tone="signal" />
    {/if}

    {#if body}
        <p class="body">{body}</p>
    {/if}

    {#if bestNext}
        <p class="next">
            <span class="next-label">Best next</span>
            <span class="next-topic">{leaf(bestNext)}</span>
        </p>
    {/if}

    {#if reasons && reasons.length > 0}
        <ul class="reasons">
            {#each reasons as reason}
                <li>{reason}</li>
            {/each}
        </ul>
    {/if}
</section>

<style>
    .slot {
        background: var(--gre-surface);
        border: 1px solid var(--gre-hairline);
        border-radius: var(--gre-radius);
        padding: 1.1rem 1.15rem;
        display: flex;
        flex-direction: column;
        gap: 0.55rem;
    }
    /* Abstention is a designed state, not an error — amber, with a left rule. */
    .insufficient_evidence {
        border-left: 3px solid var(--gre-abstain);
        background: var(--gre-abstain-weak);
    }
    /* A live, observed score — a signal-toned left rule to match the range tick. */
    .observed {
        border-left: 3px solid var(--gre-signal);
    }
    .head {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 0.5rem;
    }
    .title {
        font-size: var(--gre-fs-figure);
        font-weight: 600;
        color: var(--gre-ink);
    }
    .badge {
        font-family: var(--gre-mono);
        font-size: 0.68rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--gre-muted);
        white-space: nowrap;
    }
    .insufficient_evidence .badge {
        color: var(--gre-abstain);
    }
    .observed .badge {
        color: var(--gre-signal);
    }
    .body {
        margin: 0;
        font-size: var(--gre-fs-body);
        color: var(--gre-ink);
        line-height: 1.4;
    }
    .next {
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
        margin: 0;
    }
    .next-label {
        font-family: var(--gre-mono);
        font-size: 0.68rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--gre-muted);
    }
    .next-topic {
        font-weight: 600;
        color: var(--gre-signal);
    }
    .reasons {
        margin: 0;
        padding-left: 1.1rem;
        color: var(--gre-muted);
        font-size: 0.82rem;
        line-height: 1.5;
    }
</style>
