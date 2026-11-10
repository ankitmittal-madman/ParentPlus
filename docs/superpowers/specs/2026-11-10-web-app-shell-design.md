# Web app shell and visual foundation

Founder S1-06 and Coach/Tutor prototype reference. Add public install metadata and
brand app icons, preserving real routes/session behaviour. Use Next manifest.ts,
standalone display, /login entry, root scope, teal/paper colours,192/512 PNG icons
and180 Apple icon. Metadata has no identity/session data. Preserve browser zoom.
No service worker or private-data caching in this slice; offline capture M2-42
remains separate. Device home-screen installation needs real-device confirmation;
browser manifest/icon loading is the executable acceptance here.

Match the prototype's bottom-navigation SVG icons and raised teal Post action;
preserve all five routes, link names, current-page accessibility and touch targets.
This is a reversible style change; existing navigation and viewport checks cover it.

Implementation: headless public-manifest/icon regression RED, generate static
technical icon assets, manifest/metadata + nav styling, focused GREEN; include in
integrated full regression and scenario register. Root owns these files while the
enrolment worker owns only SQL/tests/guards. No shared file concurrent edits.
