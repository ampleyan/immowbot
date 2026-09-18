# Task 4 fix review package

Fix base: `3af4aee`
Fix head: `0f5e192`

Prior findings:
- Money strings such as `€95`/`€780` rendered as `€NaN`.
- Invalid non-empty dates created blank fact rows.

Verify both findings are addressed and no new fix-diff breakage exists.
