# Session restoration — implementation plan

1. Add failing tests for disabled mode, provider-verified user, missing session and uncertain provider responses.
2. Implement a narrow status helper using provider `getUser`, with no sensitive error details and no calls when disabled.
3. Add failing login screen tests for checking, restored session and retry; implement safe conditional display and ignore results after unmount.
4. Map all executable cases, document the limits, independently review and run the full selected quality checks.
