# Class setup preview plan

**Goal:** Add a safely labelled in-memory course/batch UI prototype while backend exposure is unfinished.

**Architecture:** The existing schedule server component embeds a small interactive client component. The form validates and previews text locally only; it performs no persistence or network calls.

**Spec:** [Class setup preview](../specs/2026-11-03-class-setup-preview.md).

1. Write component tests for blank names, valid trimmed preview and invalidation after edits; observe failure.
2. Implement the client form with accessible labels, error/status messages and no persistence. Extend the existing synthetic schedule browser case.
3. Map exact test cases and run component, lint, type, build, browser, database and quality evidence checks. Independently review before release; real application integration remains a blocker.
