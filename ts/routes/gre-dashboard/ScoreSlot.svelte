<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    const { title, body, state }: { title: string; body: string; state: string } = $props();
</script>

<section class="slot {state}">
    <h2>{title}</h2>
    <p>{body}</p>
</section>

<style>
    .slot { border: 1px dashed var(--border, #ccc); border-radius: 8px; padding: 1rem; }
    .slot h2 { margin-top: 0; }
</style>
