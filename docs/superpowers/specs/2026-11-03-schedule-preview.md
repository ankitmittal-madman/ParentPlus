# Coach schedule preview — synthetic M3 slice

## Purpose and acceptance
A coach needs to understand how their upcoming class sessions will appear. Replace the schedule placeholder with a read-only example list showing a course, batch and session time. Clearly label every example as synthetic; no dates imply that a session is actually scheduled. Keep the existing navigation and design tokens, use semantic headings and list markup, and do not show child names or private data.

## Boundaries and safety
This is an M3 presentation preview, not functional scheduling, attendance, enrollment, authorization or a database integration. It must not create or modify classes, imply a real schedule exists, connect to a hosted service or use real family data. Course, batch and session remain distinct as required by DEC-014. Exact scheduling fields and authorization need their own design before persistent data or release.

## Tests
Component and local Chromium browser tests verify that the schedule and synthetic-data notice are visible and that example course, batch and session time are displayed accessibly. Existing frontend, browser and database suites remain required by the quality gate. This slice does not replace a real scheduling end-to-end test or backend security checks.
