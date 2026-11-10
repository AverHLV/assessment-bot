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
- When `.ai/reviews/review-<task-slug>.md` exists, read it only to learn which findings and recommendations the
  developer declined: those marked `Declined` in its tables or in its `Fix Report`. Treat every other statement
  there as an unverified claim, and establish all findings from the specification and the code.

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
- the necessity or compatibility of each behavior-affecting change in the review set.

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

Report validated stability omissions as non-blocking coverage notes, not specification findings. They do not trigger
the severity gate below and must remain listed as uncovered. This exception applies only to the validated coverage
gap; rate unsupported omissions, unstable tests, and implementation defects using the normal severity rules.

Deduplicate implementation and test findings by root cause. Order them by severity, specification item, and source:

- **Critical**: permits data loss, a serious authorization breach, irreversible corruption, or unsafe operation.
- **High**: omits or contradicts a core `MUST`, success criterion, or acceptance workflow, or leaves it untested.
- **Medium**: partially implements required behavior or misses a material edge, failure, state assertion, or branch.
- **Low**: has limited behavioral impact but weakens conformance, traceability, or test precision.

Rate a query-efficiency finding Medium when a statement repeats per processed row, and Low otherwise. A reread
justified by locking or freshness, a necessary transaction-control statement, and a fixed-size batch repetition are
not findings.

Before reporting, drop a candidate finding when any of these applies:

- no realistic triggering path exists through public inputs, supported operations, or documented deployment
  conditions;
- it concerns pre-existing behavior the task did not change and the specification does not require changing; or
- it demands behavior the specification neither states nor implies, such as extra validation, configurability,
  generality, or defensive handling of states the system cannot reach.

Severity measures the consequence; it does not decide whether a fix is worth it. Mark each remaining finding with an
independent fix recommendation:

- **Fix**: the trigger is realistic and the fix is proportionate to the consequence. Critical findings, findings
  against a core `MUST`, and query-efficiency findings are always `Fix`.
- **Optional**: the finding is real, but its trigger needs rare or unusual conditions, or its smallest fix adds code,
  abstraction, or coupling that is out of proportion to the consequence. Name which reason applies.

A Low finding with a one-line fix is `Fix`. A Medium finding with a rare trigger and an invasive fix may be
`Optional`. Always propose the smallest fix that removes the consequence and that the shared implementation guidelines
would accept; never propose new layers, wrappers, or configuration that the specification does not require.

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

Report conformance and the fix decision separately. Start with one verdict line:

- `Verdict: conformant` when there are no findings at all;
- `Verdict: changes required — highest severity <level>` when any finding is marked `Fix`, using the highest severity
  among `Fix` findings; or
- `Verdict: not conformant, no required fixes — highest severity <level>` when only `Optional` or `Declined`
  findings remain, using the highest severity among them.

Append ` — N optional, M declined` when such findings exist, and ` — N stability omissions` when stability omissions
have been validated. Replace each count with the matching number; count stability omissions as distinct uncovered
scenarios.
Include:

1. the specification path and concise inventories of the review set and confirmed unrelated changes;
2. the specification-findings table and gate result;
3. the engineering-recommendations table when the gate permits Stage 4, or only the carried-over declined
   recommendations when it does not;
4. fully, partially, and uncovered specification items, including validated stability omissions with rationale and
   evidence locations as non-blocking coverage notes;
5. any proposed memory candidate; and
6. confirmation that no file other than the review artifact was written and no project code, tests, formatters, or
   migrations ran.

Do not claim completeness without evidence. Name unreadable changes and lower confidence instead of guessing.

## Save the review

Before responding, write the complete final response to `.ai/reviews/review-<task-slug>.md`, replacing any earlier
review of the task. Use the specification's task slug. Open the file with:

```markdown
# Review: <specification title>

Source request: <the specification's Source request line>
Source specification: <repository-relative path>
Specification revision: <n>
```

Take `<n>` from the specification's `Revision` line, or use 1 when the line is absent. Write every finding and
recommendation in full, because a later `fixer` run reads this file without this conversation. End the response with
the review path.
