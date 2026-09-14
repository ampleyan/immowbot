# Handoff

## State

I updated README.md to document the current buyer UI, review queue, lazy loading, galleries, comparison, duplicates, purchase markers, and scoring. The latest pushed commit is `1720178` on `master`; the worktree still has unrelated `data/buyer.db` changes and untracked `AGENTS.md`.

## Next

Review any new UI requests from the current `master` state. Run frontend tests, type-check, and build before claiming frontend work complete.

## Context

Active treats listings with workflow status `New` or unset as pending review. Other statuses remain accessible in the collapsed Reviewed listings section. Outdoor space adds a 5-point capped score bonus. Potential-benefit labels are prompts to verify eligibility, not guaranteed discounts.
