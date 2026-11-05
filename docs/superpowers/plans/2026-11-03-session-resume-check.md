# Session revalidation on return — implementation plan

1. Add failing UI tests for a returning tab whose previously confirmed session has ended and for disabled mode.
2. Add bounded focus/visibility event revalidation using the existing generation and uncertain-sign-out safeguards; remove listeners on unmount.
3. Map the tests, independently review the event races, and run the complete selected quality checks before any checkpoint.
