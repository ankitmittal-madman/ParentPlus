# Child creation database control — local draft

## Purpose and behaviour

The existing authenticated `create_child` database function can create a child and a provisional, self-declared relationship. A web interface flag cannot stop someone from calling the database function directly. Migration 034 adds a private singleton control that defaults to disabled. The function checks the database identity, locks the control row for the transaction and denies both new creation and retries if the row is missing or disabled. Its existing input, idempotency and guardian replay checks remain in place.

A denial while retrying does not prove that an earlier request failed: the earlier transaction could have committed before the control was disabled. Do not create a new request merely because a retry was denied. This change does not enable child creation, modify hosted resources, prove legal guardianship or implement the parent-facing creation journey.

## Test boundary

The fresh database initialization and final cleanup checks require exactly one disabled control row. Existing child and connection behaviour tests explicitly enable the control inside rolled-back synthetic transactions; the standalone concurrent child test temporarily enables it in the isolated disposable database so both sessions can observe it, then restores it. Separate tests use the real authenticated role to check disabled and missing controls, private control privileges, disabled retries, and both orderings of a write versus disablement. The fixture is serial and network-isolated; forced process death is handled by discarding the disposable database, not by assuming cleanup succeeded.

## Remaining release work

A parent-facing creation screen, durable recovery after a lost response or account change, explicit lifecycle and retention decisions, real signed-JWT/provider verification, production role/owner review, abuse controls and real-device end-to-end testing remain open. Do not enable the database control or use real child data until the relevant review and authorization are complete.

## Later local journey

Migration 035 later revokes authenticated execution of the legacy function and adds default-off journey wrappers. Historical tests use explicit temporary grants only in isolated synthetic fixtures; actual-role tests verify the legacy denial. See [the journey spec](2026-11-04-child-creation-journey.md).
