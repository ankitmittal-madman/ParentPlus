# Class setup server boundary plan

**Goal:** Prepare a fail-closed server-side bridge to the local atomic class-setup RPC.

**Architecture:** A Next.js server action validates input, returns immediately unless the server-only flag is exactly true, verifies the current user with the Supabase server client and calls the atomic RPC. It returns sanitized results and is not yet connected to the practice UI.

**Spec:** [Class setup server boundary](../specs/2026-11-03-class-setup-server-boundary.md).

1. Test disabled mode, malformed input, missing/failed identity, normalized RPC success, failed/thrown RPC and malformed results with synthetic doubles.
2. Implement the server action; retain database authorization as the ultimate access check and leave the flag disabled by default.
3. Map exact tests, run full local gate and independent review. Do not claim real provider, workspace selection or browser integration.
