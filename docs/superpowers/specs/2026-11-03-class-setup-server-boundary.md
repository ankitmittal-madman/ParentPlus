# Class setup server boundary

## Problem and scope

Prepare a server-only bridge from a future class-setup screen to the atomic database operation. It remains unused by the practice screen and disabled unless the server environment explicitly enables it. No hosted resource is accessed during tests. This bridge is not the completed application journey.

## Contract and threats

The server action receives unknown input containing workspace ID, request ID, expected actor ID, course and batch names. Validate UUID-shaped IDs and trimmed 1–120-character names, reject malformed input, validate the expected actor ID and pass only validated fields to the atomic RPC. The expected actor is a mismatch guard, not an authority: compare it with the verified current user and never pass it to the RPC. Before any RPC, ask Supabase Auth for the current user; reject missing/failed identity. The database must independently enforce workspace-manager authorization. Return a minimal generic result; never return provider errors, tokens or data from another workspace. Require an exact successful RPC response with two UUIDs; failures, thrown errors and malformed responses stay generic. The caller must reuse the same request ID when retrying an uncertain result and choose a new ID for changed input. Rate limiting, true JWT/provider validation, workspace selection, application integration and audit remain required before exposure.

## Tests

Use fake provider responses for disabled mode, malformed inputs, signed-out/error responses, successful RPC and malformed/failed responses. No tests should connect to hosted resources. The real signed-JWT/PostgREST path and full browser journey remain unverified.

## Independent app and database switches

The server environment flag gates this server action only; it cannot block a direct PostgREST/RPC call. The local draft combined RPC additionally checks a private singleton database control, defaulting to disabled and locked for the write transaction. App roles cannot read or change this control. The shared guard applies to the combined RPC and to the standalone course and batch creation RPCs; it does not gate unrelated operations. Neither control is permission to deploy. Pending retries are actor-scoped: the future UI must bind an uncertain retry to the original user and workspace and reconcile on account changes before offering a retry. The server action rejects an expected actor that differs from the verified current user. That is only a boundary check: the identity-switch UX and trustworthy retention of the original actor and workspace are not implemented.
