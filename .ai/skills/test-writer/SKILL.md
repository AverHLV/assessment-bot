---
name: test-writer
description: >-
  Write and run tests for an implemented SDD specification. Use when non-committed production changes must be mapped
  to the specification, covered with behavior-focused tests, formatted, and verified with the complete test suite
  while unrelated working-tree changes are preserved.
---

# Test Writer

Write behavior-focused tests for an implemented specification. Treat the specification as the acceptance authority
and task-related non-committed production changes as the implementation result.

## Boundaries

- Require one readable specification under `.ai/specs/`; never change it.
- Make intentional edits only to tests and test-support code. Do not fix production defects exposed by valid tests.
- Preserve existing changes. Formatting may modify production files only as a formatter side effect; report it.
- Use the Makefile for formatting and the complete suite. Run targeted tests only in the application container with
  the designated interpreter.

## Select the task and implementation

Read and apply the shared [SDD workflow guidelines](../../sdd-workflow-guidelines.md), with these role-specific rules:

- Allow specification artifacts only under `.ai/specs/`.
- Resolve a task slug to `.ai/specs/spec-<task-slug>.md`. Without an identifier, require exactly one specification.
- Also read `.ai/plans/plan-<task-slug>.md` when it exists. Use its `Implementation Record` as technical guidance for
  the final query budget and technical decisions, never as acceptance authority.
- Require task-related non-committed production changes. If none exist, report that there is no implementation to
  test and stop.
- Record the initial task-related and unrelated changes so later test edits and formatter effects remain attributable.

Read affected production code, adjacent tests, base test cases, assertion helpers, and factories before choosing test
placement or patterns.

Read and apply the shared [test-writing guidelines](../../test-writing-guidelines.md). When its summary differs from
actual test-support code named there, follow the code.

## Design and write coverage

Build one internal coverage matrix before editing. Map:

- every in-scope requirement, success criterion, and acceptance scenario to tests or documented stability omissions;
- every changed behavior and material implementation branch to a specification expectation where possible;
- authentication, permissions, validation, missing resources, conflicts, invalid states, and dependency failures;
- persistent state changes, external calls and non-calls, and database query counts.

Create separate tests for specified cases with distinct setup, behavior, or results. Cover changed observable behavior
even when the specification does not enumerate its internal branches, subject only to the narrow omission exception
in the shared test-writing guidelines. For untraceable behavior, test the stable contract supported by adjacent code
and report the assumption and specification gap.

Keep each test focused on one scenario without duplicating expensive setup. Use implementation knowledge to reach
branches and assert internal effects, not to replace public behavioral assertions. Preserve and extend existing
task-related tests when appropriate.

## Record stability omissions

For each omission permitted by the shared test-writing guidelines, record the specification item, exact uncovered
scenario, existing helpers and deterministic approaches considered, and why each applicable approach cannot exercise
the behavior. Include supporting code locations or attempted checks and their results; distinguish approaches ruled
out by inspection from those tried. Record the remaining deterministic coverage in the coverage matrix.

Keep this rationale in the coverage matrix and final report, and persist a concise version beside related tests or
test-support code as a comment. A later verifier must be able to assess the omission without the earlier conversation.
Do not claim the omitted scenario is covered.

## Verify and report

Run every command from the repository root:

1. Confirm the coverage matrix represents every requirement, criterion, scenario, explicit case, permission, and
   failure path. Fix clear omissions and document justified stability omissions. Mark omission candidates that need
   targeted checks as provisional until those checks provide evidence.
2. Run `make container@start`, then `make project@format`. No extra environment variables or input data are required;
   formatting updates files in place. Fix only test-related failures and report production-file side effects.
3. For iteration, run targeted tests through `make container@console` with
   `/opt/venv/app-4PlAip0Q/bin/python manage.py test --no-input <test-label>`, where the label is a dotted module,
   class, or method path such as `bot.tests.test_commands_rate`. The input is the selected test label and output is
   written to the terminal. Use the results to resolve provisional omissions: add deterministic coverage or finalize the
   documented justification before the complete-suite run and final report. Rerun formatting if tests changed.
   A targeted run never replaces the complete suite.
4. Run `make project@test` unconditionally. It starts required services, needs no extra environment variables, reads
   repository tests and test data, and writes coverage output to the locations configured by the project.
5. Fix failures caused by test or test-support code and rerun the complete suite. Keep a valid failing assertion when
   it exposes an implementation or specification defect; do not weaken it or change production code.
6. Call a failure pre-existing only with task-independent evidence. Otherwise report it as unresolved.
7. Compare the final tree with the recorded initial state and confirm intentional edits are limited to tests and test
   support.

Add at most one `.ai/memories/` entry only for a verified, non-obvious, reusable testing finding; never record task
history, assumptions, or facts already documented by the project.

Report the specification and implementation covered; changed test files; coverage of explicit cases, negative paths,
state, mocks, and queries; formatting and complete-suite results; defects, gaps, unresolved failures, formatter
effects, or assumptions; stability omissions with their rationale and evidence locations; and any memory entry.
