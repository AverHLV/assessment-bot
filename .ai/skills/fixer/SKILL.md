---
name: fixer
description: >-
  Fix the findings of a saved SDD verification review in one pass. Use when `.ai/reviews/review-<task-slug>.md` exists
  and its findings in production code and tests must be fixed, formatted, and checked with the complete test suite
  without rerunning the earlier pipeline stages.
---

# Fixer

Fix the findings of one saved verification review in production code and tests. The review is the work list, and the
specification remains the acceptance authority. Work from the artifacts alone, without the verifier's conversation.

## Boundaries

- Require one readable specification under `.ai/specs/` and its review under `.ai/reviews/`.
- Never change the specification. In the review, write only the `Fix Report` section.
- Change only what a selected finding requires. Do not add features, refactor, or clean up unrelated code.
- Never drop, merge, or reinterpret a finding. When a finding cannot or should not be fixed, say so in the
  `Fix Report` with the reason.
- Do not add or update dependencies, and do not write an implementation plan.

## Select the task and the work list

Read and apply the shared [SDD workflow guidelines](../../sdd-workflow-guidelines.md), with these role-specific rules:

- Allow artifacts only under `.ai/specs/`, `.ai/plans/`, and `.ai/reviews/`.
- Resolve a task slug to `.ai/specs/spec-<task-slug>.md` and `.ai/reviews/review-<task-slug>.md`, and require both.
  Without an identifier, require exactly one review.
- Also read `.ai/plans/plan-<task-slug>.md` when it exists, as technical guidance only.
- The review is stale when its `Specification revision` differs from the specification's `Revision`, treating a
  missing `Revision` line as 1. Report it, recommend a new `verifier` run, and stop.

Build the work list from the review, taking each entry verbatim:

- every finding marked `Fix`;
- every engineering recommendation that is not marked `Declined`; and
- an `Optional` finding only when the user names it.

Exclude an entry that the user declines in the request and record it as `Declined`. Exclude an entry that an existing
`Fix Report` already marks `Fixed` or `Declined`, and keep that status. If the work list is empty, skip fixing,
formatting, and tests: write the `Fix Report` as described below, report it, and stop.

## Fix

Read and apply the shared [implementation guidelines](../../implementation-guidelines.md) and
[test-writing guidelines](../../test-writing-guidelines.md).

1. For each entry, read the cited evidence and enough adjacent code to confirm the problem in the current working
   tree. When the evidence no longer holds, change nothing and record the entry as `Not fixed` with the
   `path:line` evidence.
2. Fix production code first, then tests. Apply the smallest change that removes the stated consequence.
3. When a production fix changes behavior, add or update the tests of that behavior in the same pass. Rebuild the
   query budget of every changed execution path, and keep exact query counts in tests equal to it.
4. When a fix changes Django models, follow the migration steps of the
   [implementer skill](../implementer/SKILL.md).
5. When a fix needs a decision that changes acceptance behavior, or a design beyond a local change, do not improvise.
   Record the entry as `Not fixed` and name the required specification revision or `implementer` run.

## Verify and report

Run every command from the repository root:

1. Run `make container@start`, then `make project@format`. No extra environment variables or input data are required;
   formatting updates files in place.
2. For iteration, run targeted tests through `make container@console` with
   `/opt/venv/app-4PlAip0Q/bin/python manage.py test --no-input <test-label>`, where the label is a dotted module,
   class, or method path such as `bot.tests.test_commands_rate`. The input is the selected test label and output is
   written to the terminal.
3. Run `make project@test` unconditionally. Fix failures caused by this pass and rerun the complete suite. Report any
   other failure as unresolved; call it pre-existing only with task-independent evidence.
4. When a fix changed a query budget and the plan file has an `Implementation Record`, update the final query budget
   there.
5. Write a `## Fix Report` section at the end of the review file, replacing an earlier one. List every finding and
   recommendation ID of the review exactly once:

| ID | Status | What changed |
|---|---|---|
| F-001 | Fixed | `bot/example.py:42` now sends the duplicate message; covered by `test_rate_duplicate`. |
| F-002 | Skipped — optional | Not requested. |
| F-003 | Not fixed — evidence no longer holds | `bot/example.py:120` already annotates the media queryset. |
| R-001 | Declined | Declined by the developer in the request. |

Use `Fixed`, `Not fixed — <reason>`, `Declined`, or `Skipped — optional` as the status. Record an entry that the
review itself marks `Declined` as `Declined`, and carry over a status that an earlier `Fix Report` already settled.
An ID without a row is an error; add the row before finishing.

Report the same table; the changed files; the formatting and complete-suite results; unresolved failures; and required
specification revisions. State that the result is unverified until a new `verifier` run in a fresh session.
