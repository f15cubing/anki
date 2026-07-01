<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    const ALLOWED_STATES = new Set(["insufficient_evidence", "not_available"]);
    const { title, body, state, reasons }: {
        title: string;
        body: string;
        state: string;
        reasons?: string[];
    } = $props();
    const safeState = $derived(ALLOWED_STATES.has(state) ? state : "not_available");
</script>

<section class="slot {safeState}">
    <h2>{title}</h2>
    <p>{body}</p>
    {#if reasons && reasons.length > 0}
        <ul class="reasons">
            {#each reasons as reason}
                <li>{reason}</li>
            {/each}
        </ul>
    {/if}
</section>

<style>
    .slot { border: 1px dashed var(--border, #ccc); border-radius: 8px; padding: 1rem; }
    .slot h2 { margin-top: 0; }
    .reasons { margin: 0.5rem 0 0; padding-left: 1.25rem; color: var(--fg-subtle, #888); font-size: 0.875rem; }
    .reasons li { margin: 0.15rem 0; }
</style>
