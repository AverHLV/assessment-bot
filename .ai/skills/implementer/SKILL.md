---
name: implementer
description: >-
  Implement a small, implementation-ready specification directly. For a large or materially uncertain task, create
  an implementation plan and stop for that turn. Use an existing compatible plan when available, and follow
  `.ai/implementation-guidelines.md` for production changes.
---

# Implementer

Implement an existing specification or prepare its implementation plan. Make only safe, task-scoped assumptions and
ask questions only when a decision materially affects architecture, data, security, external behavior, or effort.

## Boundaries

- Require a readable specification under `.ai/specs/`. User prose and a plan do not replace it.
- Never change a specification. Report required specification revisions instead.
- Treat plans as ignored local artifacts. Do not stage, commit, or present them as a shared source of truth.
- Do not write or modify tests.
- Do not add or update dependencies. Stop and request developer action when implementation needs one.

## Select the task

Read and apply the shared [SDD workflow guidelines](../../sdd-workflow-guidelines.md), with these role-specific rules:

- Allow artifacts only under `.ai/specs/` and `.ai/plans/`.
- Resolve a task slug to `.ai/specs/spec-<task-slug>.md` and an optional `.ai/plans/plan-<task-slug>.md`.
- When one task has both artifacts, select both. If a plan is selected directly, require its `Source specification`
  reference to identify an existing specification unambiguously.
- Respect plan decisions only when they remain compatible with the specification.

A specification that contains a `[NEEDS CLARIFICATION: ...]` marker is incomplete. Name the open questions, route the
task back to `spec-writer`, and stop without writing a plan or changing implementation files.

Read and apply the shared [implementation guidelines](../../implementation-guidelines.md) before planning or changing
production code.

## Analyze the change

Build an internal model of:

- observable behavior, acceptance criteria, exclusions, permissions, integrations, and failure paths;
- affected packages, data flow, migrations, compatibility, and existing conventions;
- entities, identity, relationships, validation, and state transitions;
- entry-point inputs, such as Discord app commands, view items, modals, management commands, and admin actions;
  their outputs, response messages, and database access paths.

Check each assumption in the specification against the code. When the code contradicts one, stop before writing a
plan or changing files, and report the assumption ID, the evidence, and the specification revision it requires.

Choose the smallest architecture consistent with the repository. Prefer existing patterns and dependencies. Record
only low-risk, reversible assumptions; never invent business policy, security behavior, or external contracts.

## Decide whether to plan

Follow a selected implementation-ready plan. When none exists, create `.ai/plans/plan-<task-slug>.md` and stop
without implementing if either condition applies:

- the expected change adds or modifies more than five Python files, including generated migrations; or
- the work has material uncertainty, cross-cutting design, a new integration, several dependent workflows, a
  security-sensitive feature, or an unresolved technical choice.

Use the selected artifact's task slug for the filename. Do not overwrite a plan for another task.

A plan is implementation-ready when it has no open question and its `Specification revision` equals the `Revision`
of the current specification. Treat a specification without a `Revision` line as revision 1. Otherwise the plan is
stale. Compare it with the current specification, report the differences, revise the affected parts of the plan,
update its recorded revision, and stop for that turn.

A plan file whose work order is absent or fully ticked records earlier work and leaves nothing to follow. Keep it and
update its `Implementation Record` after further changes.

## Resolve material ambiguity

Use the shared [clarification dialogue guidelines](../../clarification-guidelines.md) when the specification, the
repository, and confirmed decisions leave a material technical decision open. Do not write a plan or implementation
until the dialogue ends.

A decision that changes acceptance behavior belongs to the specification, not to the plan. Do not settle it as a
technical choice. Report the required specification revision, route the task back to `spec-writer`, and stop.

Record accepted answers under `Clarifications` in the plan or, for direct implementation, in the
`Implementation Record`. When the user ends the dialogue while a material technical decision is unresolved, write the
plan with that decision under `Open Questions` and stop. Never implement while a decision is open.

## Write the plan

Use this structure, omitting only sections that are genuinely irrelevant:

```markdown
# Implementation plan: <concise title>

Source request: <the specification's Source request line>
Source specification: <repository-relative path>
Specification revision: <n>

## Scope
## Technical Decisions
## Assumptions
## Clarifications
## Open Questions
## Work Order
## Requirement Traceability
## Data Model and Migrations
## Query Budget
## Risks
## Verification
## Implementation Record
```

Apply these rules:

- Number technical decisions `D-001`, `D-002`, and so on. State each decision and the repository evidence or
  convention behind it. Where a real alternative existed, name it and the reason for rejecting it.
- Give every assumption its basis: a specification statement, a repository-relative path, or a named convention.
- List under `Open Questions` every material technical decision that is still unresolved. Omit the section otherwise.
- Write the work order as numbered checkbox steps, `- [ ] 1. <outcome>`, ordered by dependency. Name the files each
  step adds or changes and the requirements it serves. Size each step so that it can be completed and reviewed on
  its own.
- Under `Requirement Traceability`, map every requirement and success criterion of the specification to the
  work-order steps that deliver it.
- Under `Data Model and Migrations`, describe entities, validation rules, state transitions, and migrations.
- Record the query budget of every changed execution path as the implementation guidelines require.
- Under `Verification`, list the commands to run with their working directory and required services.
- Describe changes by behavior, files, and interfaces. Do not paste the implementation into the plan.
- Add `Implementation Record` only after implementation.

## Implement

Start only with a complete specification and, when a plan is selected, an implementation-ready one. Follow the
analyzed behavior and preserve unrelated working-tree changes.

When following a plan, work through the unticked steps in order and tick each one (`- [x]`) as soon as its changes
are in place. When resuming a partly ticked plan, first confirm that the changes of the ticked steps are present in
the working tree; report a mismatch and stop. Record a deviation from the plan in the `Implementation Record` instead
of rewriting the plan's decisions.

When Django model changes require a migration, run from the repository root:

1. Run `make container@start`, then `make container@console`. No extra environment variables are required.
2. In the `/app` container shell, run
   `/opt/venv/app-4PlAip0Q/bin/python manage.py makemigrations <app_label> --name <short_description>`. The model
   change is the input; the migration is written under the app's `migrations/` package.
3. Inspect and correct only task-related generated issues. Never edit unrelated or historical migrations.
4. In the same shell, run `/opt/venv/app-4PlAip0Q/bin/python manage.py migrate` and confirm the migration applies to
   the running database.

## Verify and report

From the repository root:

1. Re-read the specification and trace every requirement, criterion, scenario, permission, failure path, migration,
   and query expectation to the implementation. Fix task-related discrepancies.
2. Rebuild the query budget from the final code, not from the plan. Follow each changed execution path through every
   dependency, helper, and model method it calls, and list each SQL statement as the query efficiency rules in the
   implementation guidelines require. Remove every unjustified repeated load, per-row query, and per-row write,
   then rebuild the budget for the changed code. Do not finish while any entry fails the rules.
3. Run `make container@start`, then `make project@format`. No extra environment variables or input data are required;
   formatting updates files in place. Fix task-related failures and rerun until successful.
4. Do not create or run tests. Review the final diff and report formatter effects outside the task scope.
5. Write the `Implementation Record` to `.ai/plans/plan-<task-slug>.md` so that later stages can read it without this
   conversation. When no plan exists, create the file with only the plan title, the `Source request`,
   `Source specification`, and `Specification revision` lines, and this section. Record the final query budget, the
   technical decisions and assumptions made outside the plan, accepted clarifications, deviations from the plan, and
   required specification revisions. Replace an earlier record instead of appending a history.

Add at most one `.ai/memories/` entry only for a verified, non-obvious, reusable finding that satisfies
`.ai/guidelines.md`; never record task history or documented facts.

If the turn produced or revised a plan and changed no production code, report the plan's path, scope, decisions,
open questions, and open risks. Otherwise report the implementation, migration status, specification conformance,
the final query budget, formatting result, applied assumptions and clarifications, required specification revisions,
the path of the implementation record, and any memory entry. Render the query budget as:

| Execution path | # | Statement | Purpose |
|---|---|---|---|
| `/rate` success | 1 | `SELECT user` | Resolve the interacting Discord user. |
| `/rate` success | 2 | `SELECT media JOIN category` | Load media available for assessment. |
| `/rate` success | Total | 2 | |
