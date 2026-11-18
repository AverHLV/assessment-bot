---
name: verifier
description: >-
  Perform a static verification of an SDD result and save it as a review artifact. Use when task-related staged,
  unstaged, and untracked changes must be checked for specification conformance, test coverage, and, when the
  severity gate permits it, engineering quality without executing project code or editing project files.
---

# Verifier

Statically review implementation and tests for a specification. Treat the specification as the acceptance authority
and inspect the entire non-committed working tree to identify the task result safely.

## Boundaries

- Require one readable specification under `.ai/specs/`.
- Write only the review artifact `.ai/reviews/review-<task-slug>.md`. Never edit, rename, format, stage, commit,
  stash, reset, restore, or otherwise change any other file.
- Do not execute project code, tests, formatters, linters, migrations, or commands that change service state.
- Do not create, recommend, or require checks that depend on live external services, agents, models, accounts, or
  credentials. Missing live external checks must not become conformance findings or review-gate failures.
- Do not write memory. Report a reusable, verified finding only as a memory candidate.
- Review existing work and report fixes; never apply them.

## Select the task and review set

Read and apply the shared [SDD workflow guidelines](../../sdd-workflow-guidelines.md), with these role-specific rules:

- Allow specification artifacts only under `.ai/specs/`.
- Resolve a task slug to `.ai/specs/spec-<task-slug>.md`. Without an identifier, require exactly one specification.
- Include task-related and ambiguous behavior-affecting changes in the review set. Inventory confirmed unrelated
  changes but exclude them from the task verdict.
- If the review set contains no implementation or test changes, report that no SDD result exists and stop.
- When `.ai/reviews/review-<task-slug>.md` exists, read it only to learn these decisions and history:
  - findings and recommendations the developer declined, marked `Declined` in its tables or in its `Fix Report`;
  - entries awaiting a decision, marked `Optional — needs decision` in its findings table or
    `Not fixed — needs decision` in its `Fix Report`;
  - the specification items that its `Fix` findings cited, together with their problems.

  Treat every other statement there as an unverified claim, and establish all findings from the specification and
  the code.
- When `.ai/plans/plan-<task-slug>.md` exists, read only its `Developer approved: <scope>` entries under
  `Clarifications`. They are the only record of approved extra scope, as the shared implementation guidelines
  define. Do not use the plan as acceptance evidence.

Treat requirements, `MUST` statements, success criteria, scenarios, constraints, assumptions, and explicit test cases
as the verification authority. Report a blocking clarification marker or contradiction as a specification finding;
never invent the missing requirement.

Read changed files in full and enough adjacent code to understand entry points, data flow, models, querysets, forms,
migrations, base test cases, factories, and conventions. Label each review-set change as implementation, migration,
test, test support, configuration, or ambiguous. Require each behavior-affecting change to trace to the specification.

## Stage 1: Verify implementation conformance

Build one internal traceability matrix from every in-scope requirement, criterion, scenario, constraint, and material
edge case to concrete `path:line` evidence. Verify:

- public inputs, outputs, statuses, errors, permissions, and state transitions;
- entities, relationships, uniqueness, validation, defaults, migrations, and compatibility;
- required failures, conflicts, retries, idempotency, external calls, and transaction behavior;
- database access capable of producing the required result;
- query efficiency of every changed execution path: follow it through dependencies, helpers, and model methods, and
  check each statement against the query efficiency and query budget rules in the shared
  [implementation guidelines](../../implementation-guidelines.md); and
- the necessity or compatibility of each behavior-affecting change in the review set, including extra scope, as
  the shared implementation guidelines define it, that neither the specification requires nor a recorded
  developer approval covers. Report such extra scope under `Scope / no matching spec item`, with its removal
  or the simplest mechanism that satisfies the stated cases as the fix.

Follow control and data flow. Filenames, comments, declarations, and type signatures alone are not evidence. Record
absent, partial, contradictory, and out-of-scope behavior as specification-related findings.

## Stage 2: Verify test coverage

Read and apply the shared [test-writing guidelines](../../test-writing-guidelines.md), using the actual support files
named there as the authority. Assess coverage at the project's isolated integration boundary, with deterministic
mocks or fakes for external dependencies. For agent or model requirements, review contract wiring, supplied context,
exposed tools, authorization, persistence, and handling of controlled responses and failures. Scripted replies prove
application handling, not live model judgment; live agent evaluations are not required for coverage or conformance.

Extend the same traceability matrix from acceptance-critical items to test setup, execution, and assertions.
Verify that tests:

- exercise distinct scenarios, explicit cases, success behavior, and required negative paths;
- assert the public result, persistent state, external calls and non-calls, and exact query counts where applicable,
  where each count matches the query budget of its path and does not lock in a redundant statement;
- use meaningful preconditions that reach the intended branch and would fail for incorrect behavior;
- satisfy the shared stability rules, allowing controlled concurrency and timeouts used only as hang guards;
- cover required migrations or data transitions; and
- follow repository conventions for integration boundaries, base test cases, factories, user binding, and mocks.

Treat written tests as unverified execution evidence because this workflow never runs them. Count a pre-existing test
only when its setup and assertions demonstrably exercise the changed behavior. Record missing cases, weak assertions,
unreachable setup, over-mocking, and untested specified behavior. Distinguish a weak test from a production defect
exposed by a valid test.

Flag tests whose expected outcome depends on uncontrolled scheduling, guessed sleeps, or real deadlines as coverage
findings; do not count them as reliable coverage. Assess severity from the behavior left without reliable coverage.

Read omission comments beside related tests or test-support code and any supplied test-writer report. Independently
check each claimed stability omission against the shared exception: inspect the exact scenario, existing helpers,
deterministic approaches considered, and code evidence or attempt results explaining why they cannot cover it.
Confirm that deterministically testable negative paths and surrounding workflows remain covered. An unsupported
"timing-sensitive" label is not a justified omission. Record validated omissions as uncovered in the traceability
matrix, with their rationale and evidence locations.

## Stage 3: Report specification findings and apply the gate

Report validated stability omissions as non-blocking notes, not specification findings. They do not trigger the
severity gate below and must remain listed as uncovered in the `Notes` section of the response. This exception
applies only to the validated coverage gap; rate unsupported omissions, unstable tests, and implementation defects
using the normal severity rules.

Deduplicate implementation and test findings by root cause. When several failures come from one mechanism, report
the mechanism once instead of one finding per path. This also applies when the previous review reported a failure
from the same mechanism. The fix is the mechanism's removal when it is unapproved extra scope, or one general fix
that covers every path. When a problem returns because the previous fix covered only some cases, propose a fix for
the whole class instead of the next case. Examples are one exception type, one word form, or one call site.

Order findings by severity, specification item, and source:

- **Critical**: permits data loss, a serious authorization breach, irreversible corruption, or unsafe operation.
- **High**: omits or contradicts a core `MUST`, success criterion, or acceptance workflow, or leaves it untested.
- **Medium**: partially implements required behavior or misses a material edge, failure, state assertion, or branch.
- **Low**: has limited behavioral impact but weakens conformance, traceability, or test precision.

Rate a query-efficiency finding Medium when a statement repeats per processed row, and Low otherwise. A reread
justified by locking or freshness, a necessary transaction-control statement, and a fixed-size batch repetition are
not findings. Use `Query efficiency` only when the consequence is the redundant statements themselves. When the same
code also has a behavioral consequence, such as state left inconsistent after a failure, cite the specification item
of that behavior. Decide its fix recommendation in the normal order, and mention the redundant statements in the
same finding.

Before reporting, drop a candidate finding when any of these applies:

- no realistic triggering path exists through public inputs, supported operations, or documented deployment
  conditions;
- it concerns pre-existing behavior the task did not change and the specification does not require changing; or
- it demands behavior the specification neither states nor implies, such as extra validation, configurability,
  generality, or defensive handling of states the system cannot reach.

Severity measures the consequence; it does not decide whether a fix is worth it. The fix recommendation checks the
finding's scope and necessity.

Use the definitions of a stated case and of extra scope from the shared
[implementation guidelines](../../implementation-guidelines.md). An input that the reviewer chooses to illustrate a
broad goal is never a stated case, even when the reviewer cites the criterion. A stated case does fail when the
implementation adds a condition on a detail that the case leaves open, and an ordinary instance of the case then
fails. Such details include the layout, wording, order, or formatting of model output.

Decide the fix recommendation in this order and stop at the first match:

1. A Critical finding is `Fix`. When a decision is pending for it, say so in `What should be fixed`.
2. Apply the late-round limit. A review is a follow-up round when a previous review of the task exists. In a
   follow-up round, a Medium or Low finding is `Optional — late round` unless a stated case fails or it repeats the
   same unresolved problem as a `Fix` finding of the previous review. A repeated problem continues to the next step,
   with a fix that covers its whole class. High findings continue to the next step.
3. These findings are `Fix`:
   - a finding where a stated case fails;
   - a query-efficiency finding whose consequence is only redundant statements; and
   - an unapproved extra-scope finding whose removal or simplification is proportionate.
4. Check scope. The finding is `Optional`, with the reason named in the column, when one of these applies:
   - **beyond stated cases**: every stated case of the requirement passes, and the finding extends a general
     requirement to inputs, languages, forms, or conditions that no stated case exercises;
   - **needs decision**: the smallest fix requires extra scope that neither the specification requires nor a
     `Developer approved` entry in the plan covers. Also use it for the same unresolved problem that the
     previous review carried as awaiting a decision, until the developer decides or the specification changes;
   - **repeated item**: the previous review had a `Fix` finding on the same specification item with a different
     problem, so the item may be underspecified and needs the developer's decision rather than another fix round.
     A finding that repeats the same unresolved problem is not a repeated item. Neither is a finding about the
     mechanism behind an earlier finding.
5. Check necessity. The finding is `Optional`, with the reason named, when:
   - **rare trigger**: the trigger needs rare or unusual conditions; or
   - **disproportionate fix**: the smallest fix adds code, abstraction, or coupling that is out of proportion to the
     consequence.
6. Otherwise the finding is `Fix`: the trigger is realistic, it stays within the stated cases, and the fix is
   proportionate. This includes a Low finding with a one-line fix.

A finding against a `MUST` is not `Fix` by itself. Write the column as `Optional — <reason>`, for example
`Optional — beyond stated cases`. Before carrying forward an entry awaiting a decision, confirm that its problem still
holds in the current code; drop it when it does not. Code that implements scope the developer approved is not an
out-of-scope finding.

Always propose the smallest fix that removes the consequence and that the shared implementation guidelines would
accept; never propose new layers, wrappers, or configuration that the specification does not require. In `What should
be fixed`, state concretely what that fix requires, so that the fix recommendation can be checked against it. Do not
add expected behavior that the specification does not state, such as excluding extra matches, to a proposed fix or
its test.

Check the proposed fix against the extra-scope definition in the same way as the code. A proposed fix may require
that something must be withheld, handled, preserved, or rejected only when it cites the specification item that
requires it. Drop any part without such an item. When the remaining fix still needs extra scope, mark the finding
`Optional — needs decision` instead of proposing that scope as part of a `Fix`.

Do not include cleanup that the consequence does not require. Leave text, instructions, prompts, or documentation
alone when they no longer cause the failure once the fix is in place. Change a stored or migrated artifact, such as
a prompt delivered by a data migration, only when that artifact itself causes the failure and no code change removes
it. Prefer a code-only fix otherwise. Give each failure path that the finding describes its own check in the
proposed tests.

Mark a finding as `Declined`, instead of reporting it again as `Fix` or `Optional`, when it still describes the same
problem and the developer explicitly declined it in this conversation or the previous review marks it `Declined` in
its findings table or `Fix Report`. Match by the problem, not by ID, because every review renumbers its IDs. Keep a
declined finding in the table so that the decision survives the replacement of the review.

Number the findings `F-001`, `F-002`, and so on in table order, and render them as:

| ID | Severity | Fix? | Spec item | Evidence | Problem | What should be fixed |
|---|---|---|---|---|---|---|
| F-001 | High | Fix | FR-001 | `bot/example.py:42` | Required behavior is absent. | Implement it and prove it with a test. |
| F-002 | Medium | Optional — rare trigger | FR-004 | `bot/example.py:88` | Two concurrent submissions of one assessment show the generic error instead of the duplicate message. | Catch the integrity error and send the duplicate message. |
| F-003 | Medium | Fix | Query efficiency | `bot/example.py:120` | The assessment count is selected once per listed media. | Annotate the media queryset with the count. |
| F-004 | Medium | Optional — beyond stated cases | FR-007 | `bot/example.py:150` | The stated media search example passes, but a title in another script is not found. | Matching titles across scripts requires transliteration per language; decide whether FR-007 needs it. |

Use `None` when there are no findings. Every finding must identify a specification item, `Query efficiency` for a
redundant-statement finding, or `Scope / no matching spec item` for an ambiguous, untraceable, or out-of-scope change.
Show the observable consequence and a concrete fix.

Proceed to Stage 4 only when no Critical, High, or Medium finding is marked `Fix`. Otherwise stop and state that the
conformance gate prevented code review. `Optional`, `Declined`, and Low findings do not trigger the gate. Return later
conformance discoveries to this table and reapply the gate.

When the gate prevents Stage 4, still render the engineering-recommendations table with only the recommendations
that the previous review marks as declined, in its table or its `Fix Report`. Copy each one without reassessing it,
renumber it, and start its `Recommended change` with `Declined:`. This keeps the decline decisions when the review
is replaced. Omit the table when there is none to carry over.

## Stage 4: Review engineering quality

Read and apply the shared [implementation guidelines](../../implementation-guidelines.md). Review every change in the
task review set for:

- Python correctness, typing, exceptions, async boundaries, naming, duplication, and maintainability;
- Django models, managers and querysets, forms, admin, settings, and migrations;
- discord.py cogs, app commands, views, modals, user binding, interaction responses, errors, and blocking work in
  asynchronous handlers;
- Django ORM transactions, asynchronous ORM use, loading, selected fields, N+1 access, bulk work, concurrency, and
  constraints;
- PostgreSQL integrity, locking, nullable and default behavior, indexes, and migration safety;
- trust-boundary validation, disclosure, unsafe input, compatibility, and dependency use; and
- test isolation, determinism, assertions, mocks, query counts, and maintainability.

Report only actionable recommendations supported by current changes. Do not assign severity or repeat specification
findings. Number the recommendations `R-001`, `R-002`, and so on. Keep a recommendation that still applies and that
the developer declined, by the same rule as for findings, in the table, and start its `Recommended change` with
`Declined:`.

| ID | Location | Observation | Recommended change | Rationale |
|---|---|---|---|---|
| R-001 | `bot/example.py:42` | Full rows are loaded for existence. | Use `aexists()`. | Avoid row materialization. |

Use `None` when there are no recommendations.

## Final response

The final chat response and the saved review are the same Markdown document. Print the complete document in the
chat response. Do not reply with only a summary, a list of finding IDs, or a reference to the saved file.

Render every table as a Markdown table with exactly the columns shown in Stage 3 and Stage 4, one row per finding or
recommendation. Never replace a table, or rows of it, with prose, bullet lists, or headings per finding, even when
cells are long or the response becomes long. A table without rows is written as `None` under its heading.

Use this outline, in this order:

```markdown
# Review: <specification title>

Source request: <the specification's Source request line>
Source specification: <repository-relative path>
Specification revision: <n>

**<verdict line>**

<at most three sentences on the required fixes and the gate result>

## Specification findings

<specification-findings table, or None>

<gate result>

## Engineering recommendations

<engineering-recommendations table, or None>

## Notes

<validated stability omissions, memory candidate or None, and confirmation of what was written and run>

Review path: `.ai/reviews/review-<task-slug>.md`
```

Use one verdict line:

- `Verdict: conformant` when there are no findings at all;
- `Verdict: changes required — highest severity <level>` when any finding is marked `Fix`, using the highest severity
  among `Fix` findings; or
- `Verdict: not conformant, no required fixes — highest severity <level>` when only `Optional` or `Declined`
  findings remain, using the highest severity among them.

Append ` — N optional, M declined` when such findings exist, and ` — N stability omissions` when stability omissions
have been validated. Replace each count with the matching number and omit any part whose count is zero, for example
` — 2 optional` rather than ` — 2 optional, 0 declined`. Count stability omissions as distinct uncovered scenarios.

Fill the sections as follows:

1. `Specification findings`: the full Stage 3 table and the gate result.
2. `Engineering recommendations`: the Stage 4 table when the gate permits Stage 4, or only the carried-over declined
   recommendations when it does not. Write `None` when there is nothing to show, and add that the gate prevented
   code review when it did.
3. `Notes`: each validated stability omission in one line with its uncovered scenario, rationale, and evidence
   location; any proposed memory candidate; and confirmation that no file other than the review artifact was
   written and no project code, tests, formatters, or migrations ran.

Keep the traceability matrix and the review-set inventory internal. Do not add a scope, coverage, or inventory
section to the response.

Do not claim completeness without evidence. Name unreadable changes and lower confidence instead of guessing.

## Save the review

Before responding, write the document described in `Final response` to `.ai/reviews/review-<task-slug>.md`,
replacing any earlier review of the task. Use the specification's task slug. Take `<n>` from the specification's
`Revision` line, or use 1 when the line is absent. Write every finding and recommendation in full, because a later
`fixer` run reads this file without this conversation. Then print the same document, tables included, as the chat
response.
