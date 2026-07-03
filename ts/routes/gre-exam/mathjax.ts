// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

/* eslint
@typescript-eslint/no-explicit-any: "off",
 */

// MathJax typesetting for the Exam Mode webview. The exam renders items outside
// Anki's reviewer, so it loads its own MathJax (SVG output — self-contained, no
// external font files, works offline like the rest of the deck). Content is
// prose with inline `\(...\)` / display `\[...\]` spans, so we use
// `typesetPromise` (delimiter scan of a DOM node) rather than a single-expression
// `tex2svg`. The MathJax global config MUST be set before the engine module runs,
// so we set it and then dynamically import the engine.

let enginePromise: Promise<void> | null = null;

function loadEngine(): Promise<void> {
    if (!enginePromise) {
        (globalThis as any).MathJax = {
            tex: {
                inlineMath: [["\\(", "\\)"]],
                displayMath: [["\\[", "\\]"]],
                processEscapes: false,
                processEnvironments: false,
                processRefs: false,
            },
            startup: { typeset: false },
        };
        enginePromise = import("mathjax/es5/tex-svg-full").then(
            () => (globalThis as any).MathJax.startup.promise,
        );
    }
    return enginePromise;
}

/** Typeset any `\(...\)` / `\[...\]` math inside the given DOM nodes. */
export async function typesetMath(nodes: HTMLElement[]): Promise<void> {
    if (nodes.length === 0) {
        return;
    }
    await loadEngine();
    const MathJax = (globalThis as any).MathJax;
    try {
        MathJax.typesetClear?.(nodes);
        await MathJax.typesetPromise(nodes);
    } catch (error) {
        // Never let a math-render failure break the exam UI.
        console.error("MathJax typeset failed", error);
    }
}
