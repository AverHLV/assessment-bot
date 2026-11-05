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

Treat a `[NEEDS CLARIFICATION: ...]` marker as unresolved. Do not implement while it can affect scope, correctness,
security, data, an external contract, or acceptance behavior. Name the blocking decision and required input, then stop
with implementation files unchanged.

Read and apply the shared [implementation guidelines](../../implementation-guidelines.md) before planning or changing
production code.

## Analyze the change

Build an internal model of:

- observable behavior, acceptance criteria, exclusions, permissions, integrations, and failure paths;
- affected packages, data flow, migrations, compatibility, and existing conventions;
- entities, identity, relationships, validation, and state transitions;
- entry-point inputs, such as Discord app commands, view items, modals, management commands, and admin actions;
  their outputs, response messages, and database access paths.

Choose the smallest architecture consistent with the repository. Prefer existing patterns and dependencies. Record
only low-risk, reversible assumptions; never invent business policy, security behavior, or external contracts.

## Decide whether to plan

Follow a selected implementation-ready plan. When none exists, create `.ai/plans/plan-<task-slug>.md` and stop
without implementing if either condition applies:

- the expected change adds or modifies more than five Python files, including generated migrations; or
- the work has material uncertainty, cross-cutting design, a new integration, several dependent workflows, a
  security-sensitive feature, or an unresolved technical choice.

Use the selected artifact's task slug for the filename. Do not overwrite a plan for another task.

After its title, a new plan must repeat the `Source request` line of its specification, followed by
`Source specification: <repository-relative path>`. Include scope, affected files and work order, requirement
traceability, entity and validation rules, migrations, the query budget of every changed execution path, assumptions,
accepted clarifications, technical decisions, risks, and verification commands.

## Resolve material ambiguity

Use the shared [clarification dialogue guidelines](../../clarification-guidelines.md) when no safe default resolves a
material technical decision. Do not write a plan or implementation until the dialogue ends.

Record accepted answers in a new plan or, for direct implementation, in the final report. Recommend revising the
specification when an answer changes its acceptance authority. A new plan may retain at most three unresolved markers;
do not implement while any remaining decision lacks a safe default.

## Implement

Start only with an implementation-ready specification and a compatible selected plan, if any. Follow the analyzed
behavior and preserve unrelated working-tree changes.

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

Add at most one `.ai/memories/` entry only for a verified, non-obvious, reusable finding that satisfies
`.ai/guidelines.md`; never record task history or documented facts.

If a plan was created, report its path, scope, decisions, and open risks. Otherwise report the implementation,
migration status, specification conformance, the final query budget, formatting result, applied assumptions and
clarifications, required specification revisions, and any memory entry. Render the query budget as:

| Execution path | # | Statement | Purpose |
|---|---|---|---|
| `/rate` success | 1 | `SELECT user` | Resolve the interacting Discord user. |
| `/rate` success | 2 | `SELECT media JOIN category` | Load media available for assessment. |
| `/rate` success | Total | 2 | |
