---
name: workflow-gate
description: Enforce a compact task contract and phase-gated workflow for code-changing, multi-step, or debugging requests. Use automatically when work may modify files, configuration, infrastructure, or project artifacts.
---

# Workflow Gate

Use a tight task contract before taking implementation actions.

## Route the request

For a simple question or explanation, answer directly.

For a tiny, clearly bounded edit, state the intended file, change, and verification command, then proceed.

For any broader, ambiguous, risky, or multi-file task, pause and classify it:

- Quick: one bounded change in one area.
- Standard: a feature or fix with up to two independent workstreams.
- Large: cross-project work, migrations, deployments, broad refactors, or three or more workstreams.

## Repair unclear requests

If the request does not establish a usable goal, scope, acceptance checks, and stop condition, do not inspect or edit yet. Write exactly:

Suggested prompt:

```text
[copy-pasteable prompt preserving the user's intent]
```

The prompt must contain:

- Goal
- Scope
- Acceptance checks
- Stop condition

End with: Use this prompt?

If the missing detail can be safely inferred without changing the task, infer it and continue.

## Contract

Before implementation, state:

- Mode
- Goal
- Scope
- Acceptance checks
- Stop condition

For Standard and Large work, inspect first and present a plan. Wait for explicit approval before editing unless the user has already approved the same concrete plan.

## Phase control

Keep the work in this order:

1. Inspect
2. Plan
3. Implement
4. Verify
5. Handoff

Do not combine unrelated tasks in one phase. If the request changes direction or expands scope, stop and restate the contract.

After two unsuccessful fix attempts, stop patching. Re-read the relevant code top-to-bottom, state the failed mental model, and propose the smallest revised approach.

## Verification gate

Before claiming completion, run the project's applicable type-check, lint, tests, and build checks. Report exact results and any checks that do not exist.

## Handoff

End completed work with:

```text
Changed:
Verified:
Remaining:
Next step:
```

Keep this skill short. Use the project's AGENTS.md and available specialized skills for detailed technical rules.
