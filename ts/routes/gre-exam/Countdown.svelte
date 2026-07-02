<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!-- Persistent whole-session countdown (the real exam has one global clock). -->
<script lang="ts">
    import { formatClock } from "./lib";

    const { secondsLeft }: { secondsLeft: number } = $props();
    const low = $derived(secondsLeft <= 300); // final 5 minutes
</script>

<span class="clock" class:low aria-label="time remaining">
    {formatClock(secondsLeft)}
</span>

<style>
    .clock {
        font-family: var(--gre-mono);
        font-variant-numeric: tabular-nums;
        font-size: 1.05rem;
        font-weight: 600;
        color: var(--gre-ink);
        letter-spacing: 0.02em;
    }
    .low {
        color: var(--gre-abstain);
    }
</style>
