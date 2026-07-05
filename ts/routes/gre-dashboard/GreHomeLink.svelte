<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<!--
GreHomeLink — a small, unobtrusive "← Home" affordance shared by the GRE surfaces
(dashboard, method, exam) so a learner can always get back to GRE Home. Clicking it
fires the `gre:home` webview bridge command; the Qt host
(`aqt.gre_home.handle_gre_home`, wired via `aqt.gre.nav.install_gre_home_bridge`)
focuses/opens GRE Home and closes the calling dialog.

Rendered only once the webview bridge is actually connected, so it never shows as a
dead control in a plain-browser / HMR preview: the QWebChannel bridge is injected at
DocumentReady and assigns `window.bridgeCommand` asynchronously, so we poll briefly
in onMount rather than reading availability once at (possibly pre-bridge) init.
-->
<script lang="ts">
    import { onMount } from "svelte";

    import { bridgeCommand, bridgeCommandsAvailable } from "@tslib/bridgecommand";

    let available = $state(false);

    onMount(() => {
        if (bridgeCommandsAvailable()) {
            available = true;
            return;
        }
        // The bridge connects asynchronously; poll for up to ~2s, stopping as soon
        // as it's up (or giving up quietly in a bridge-less preview).
        let tries = 0;
        const id = setInterval(() => {
            if (bridgeCommandsAvailable()) {
                available = true;
                clearInterval(id);
            } else if (++tries > 20) {
                clearInterval(id);
            }
        }, 100);
        return () => clearInterval(id);
    });
</script>

{#if available}
    <div class="gre-home-link-wrap">
        <button
            type="button"
            class="gre-home-link"
            onclick={() => bridgeCommand("gre:home")}
        >
            ← Home
        </button>
    </div>
{/if}

<style>
    .gre-home-link-wrap {
        margin-bottom: 0.45rem;
    }
    .gre-home-link {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.1rem 0;
        border: none;
        background: none;
        font-family: var(--gre-mono);
        font-size: var(--gre-fs-eyebrow);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--gre-muted);
        cursor: pointer;
        transition: color 0.15s ease;
    }
    .gre-home-link:hover {
        color: var(--gre-signal);
    }
    .gre-home-link:focus-visible {
        outline: 1px solid var(--gre-signal);
        outline-offset: 3px;
        border-radius: 3px;
        color: var(--gre-signal);
    }
    @media (prefers-reduced-motion: reduce) {
        .gre-home-link {
            transition: none;
        }
    }
</style>
