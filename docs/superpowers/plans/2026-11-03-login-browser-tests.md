# Login browser tests — implementation plan

1. Write Chromium tests for the local login page and run them before adding the harness; confirm the missing harness causes the expected failure.
2. Add a pinned Playwright test dependency and local-only test configuration with a disabled-OTP production server; run the tests with available Chromium.
3. Run the browser suite as a mandatory step of the existing frontend CI workflow; retain unit-test evidence and fail on browser failures.
4. Update test documentation and independently review the harness, safety constraints and CI execution; run the full local quality checks for the resulting source snapshot.
