# Intelligent Quality Gate v1 design

The supplied implementation brief is the approved scope. Build a standard-library Python engine and JSON registry/policy. Discover Python cases through unittest collection, standalone scenarios from the existing runner, and frontend cases through Vitest's JSON collector. A registry reference is an exact collected test identity, not a claimed passing result.

Selection always runs gate tests and registry validation. Frontend presentation changes run frontend checks; database changes run the complete isolated database suite; authentication, shared dependencies, CI, gate configuration and unknown paths run both. Protected minimum rules in the engine reject policy weakening. A documentation-only change still validates the registry and gate. Missing/unreliable Git comparison selects everything.

Reuse existing workflows via workflow_call, moving automatic event orchestration to intelligent-quality.yml to avoid duplicate expensive runs. Preserve every existing frontend/database check and the GitLab mirror unchanged. The final job requires selected jobs to succeed and validates uploaded exact-case JUnit evidence against the plan and Git commit. Artifacts are downloaded from the same workflow run. No privileged pull_request_target or external API/check polling is necessary.

Alternative: wait for independent workflow checks via the GitHub API. Rejected because event timing, branch filters, commit association and fork permissions make reliable verification more complex. Alternative: run new copies of existing shell jobs. Rejected because duplicated checks drift.

Coverage means explicitly linked scenarios, not complete product correctness. Planned/deferred features remain nonblocking gaps. Implemented high/critical requirements must have covered executable scenarios. Every collected existing test must be mapped. Runtime evidence and a selection plan are separate outcomes. No AI service, live OTP or production database is involved.
