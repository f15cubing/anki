<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import { onMount } from "svelte";
    import MemoryPanel from "./MemoryPanel.svelte";
    import CoverageMap from "./CoverageMap.svelte";
    import ScoreSlot from "./ScoreSlot.svelte";

    let vm: any = $state(null);
    let error: string | null = $state(null);

    onMount(async () => {
        try {
            const resp = await fetch("/_anki/greDashboardData", {
                method: "POST",
                headers: { "Content-Type": "application/binary" },
                body: new Uint8Array(),
            });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            vm = await resp.json();
        } catch (e) {
            error = String(e);
        }
    });
</script>

<div class="gre-dashboard">
    <h1>GRE readiness</h1>
    {#if error}
        <div class="err">Couldn't load dashboard: {error}</div>
    {:else if !vm}
        <div>Loading…</div>
    {:else}
        <MemoryPanel memory={vm.memory} generatedAt={vm.generated_at} />
        <div class="slots">
            <ScoreSlot
                title="Performance"
                body={vm.performance.note}
                state={vm.performance.state} />
            <ScoreSlot
                title="Readiness"
                body={`Insufficient evidence to score — studied ${Math.round(
                    vm.readiness.studied_pct * 100,
                )}% of topics. Best next: ${vm.readiness.next_best_topic ?? "—"}.`}
                state={vm.readiness.state} />
        </div>
        <CoverageMap coverage={vm.coverage} />
    {/if}
</div>

<style>
    .gre-dashboard { padding: 1rem 1.5rem; max-width: 1000px; margin: 0 auto; }
    .slots { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1rem 0; }
    .err { color: var(--fg-critical, #c00); }
</style>
