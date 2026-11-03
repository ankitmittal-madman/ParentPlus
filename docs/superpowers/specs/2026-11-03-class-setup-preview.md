# Class setup preview

## Problem and scope

Indian coaches need a simple way to understand course and batch setup. Add a clearly labelled practice-only form to the existing example schedule. It displays a trimmed course and batch preview in browser memory only and never saves, sends, schedules or grants access. Do not ask for child or family data. This is a UI prototype, not the real class-management journey.

## Acceptance and threats

Both names are required after trimming and each must contain at most 120 characters. Report errors accessibly without displaying a successful preview. Changing either field removes an outdated preview; valid input shows the exact trimmed names and an explicit unsaved message. React text rendering escapes input. No network request or storage is used. Real authentication, authorization, persistence, coach selection, duplicate handling, actual accessibility/device review and end-to-end integration remain required before release.

## Dependencies and tests

The schedule page embeds an isolated client component; no database, environment flag or provider dependency is introduced. Test empty/whitespace input, valid preview, stale-preview clearing and browser interaction. Keep existing example schedule tests intact and map exact test identities.
