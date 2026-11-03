# Session change safety — implementation plan

1. Write failing subscription tests for disabled mode, ignored initialization, change notification and cleanup; implement the smallest subscription wrapper.
2. Write failing UI tests for stale async completions, event-driven revalidation and sign-out uncertainty. Use deferred promises and synthetic events; do not use a hosted provider.
3. Add cancellable generation-based invalidation and defer provider checks until the SDK callback has returned. Verify callback cleanup and unavailable behavior.
4. Map executable scenarios, obtain independent adversarial review, address findings and run the full local quality gate. Record remaining live-provider and expiry limitations.
