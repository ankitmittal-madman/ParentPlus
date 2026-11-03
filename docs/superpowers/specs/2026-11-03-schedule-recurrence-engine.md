# Scheduling recurrence engine — local foundation

## Product problem
A coach needs one-off and weekly sessions to retain their intended local start time in the workspace time zone. This local utility validates and expands an explicit bounded date range into UTC instants. It contains no child data, does not create bookings or grant schedule permissions, and must not be treated as the authoritative backend.

## Behavior and boundaries
Accept a strict ISO local date and minute, an IANA workspace time zone, duration in whole minutes and either one occurrence or weekly recurrence through an inclusive end date. Return ordered UTC start/end instants; durations are elapsed minutes. End instants beyond year 9999 use extended ISO year notation, which future consumers must explicitly support or reject before integration. Reject invalid dates, times, zones, durations, reversed bounds and local times that are ambiguous or nonexistent due to daylight-saving changes. Users must resolve those times; do not guess an offset. Limit local expansion to 104 occurrences and duration to 1–1440 minutes as explicit engineering resource guards, not a final product retention policy.

The future backend must independently enforce authorization, assignment, idempotency, concurrency, canonical workspace time zone and recurrence validity. Individual/future edits, schedule persistence, visibility, overlap, cancellation and real user journeys are not implemented by this engine. Follow DEC-018 and DEC-019.

## Tests
Verify one-off and inclusive weekly cases, UTC conversion, offset changes, daylight-saving gaps and overlaps, invalid fields, duration/bounds, and the occurrence limit. No hosted provider or real family data is involved. Requirements must map exact collected tests; run the full local gate and independent review.
