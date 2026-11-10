export type Action = { route: string; name: string; kind: string };

export function installActionObserver() {
      const stableNames = new WeakMap<Element, string>();
      const name = (element: Element) => {
        const clone = element.cloneNode(true) as Element;
        clone.querySelectorAll('[aria-hidden="true"]').forEach(node => node.remove());
        const value = (element.getAttribute("aria-label") || clone.textContent || "").replace(/\s+/g, " ").trim();
        if (["Saving…", "Creating…", "Sending...", "Verifying...", "Signing out...", "Signing out…"].includes(value)) return stableNames.get(element) || "";
        stableNames.set(element, value);
        return value;
      };
      const record = (element: Element, kind: string) => {
        const w = window as unknown as { qaRecord: (a: Action) => Promise<void> };
        const label = name(element);
        if (label) void w.qaRecord({ route: location.pathname, name: label, kind });
      };
      document.addEventListener("click", event => {
        const element = (event.target as Element)?.closest("button,a,summary");
        if (element) record(element, "clicked");
      }, true);
      const observe = () => document.querySelectorAll("button,a,summary").forEach(element => {
        if (element.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) record(element, "observed");
      });
      window.addEventListener("DOMContentLoaded", () => {
        let scheduled = false;
        new MutationObserver(() => {
          if (!scheduled) { scheduled = true; requestAnimationFrame(() => { scheduled = false; observe(); }); }
        }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["style", "class", "hidden", "open", "disabled", "aria-hidden"] });
        observe();
      });
}
