---
name: spec-writer
description: >-
  Create or revise a testable SDD specification from a task description. Use when an informal request, user
  stories, documentation, constraints, or related context must become a solution-neutral artifact under `.ai/specs/`
  without changing implementation files.
---

# Spec Writer

Create an implementation-ready, technology-aware but solution-neutral specification. Ground it in the current system,
ask about every material decision that the source and the repository leave open, and assume only low-impact,
reversible details.

## Boundaries

- Require a non-empty prose description of the task. If it is absent, say so and stop without writing.
- Write only `.ai/specs/spec-<task-slug>.md`; never change implementation, plans, tests, or configuration.
- Treat the specification as an ignored local artifact. Do not stage, commit, or present it as shared truth.
- Never invent business policy, legal obligations, security guarantees, external API behavior, or service targets
  when no safe default exists.
- Keep private reasoning, raw coverage assessments, scoring, and unused questions internal.

## Validate and gather input

1. Read and apply the shared [SDD workflow guidelines](../../sdd-workflow-guidelines.md) for naming and selecting
   specifications.
2. To revise a specification, select it as those guidelines require. Otherwise list `.ai/specs/`, read the opening
   `Source request` line of each specification, and read every candidate completely. When one specification
   unambiguously covers the same feature, revise it; otherwise derive a new task slug from the description.
3. Apply the shared project-memory rules from the same guidelines. Do not search unrelated files or the internet
   unless the user requests it or referenced material requires verification.
4. Ground the request in the current system. Read the Discord cogs, app commands, views, modals, models, forms,
   admin, management commands, settings, and tests that the described behavior touches, and enough adjacent code to
   establish the current behavior, terminology, and contracts. Limit reading to the affected area. Treat what the code
   shows as a fact supported by a repository-relative path; never ask the user about it or record it as an
   assumption. Report a conflict between the request and the current behavior as a candidate question instead of
   resolving it silently.
5. When revising, keep the existing filename and update its `Source request` line only when the scope changes. Do not
   discard confirmed content or restructure it merely to fit a template. Ask which source governs before replacing a
   confirmed decision.
6. When revising, also read `.ai/plans/plan-<task-slug>.md` and `.ai/reviews/review-<task-slug>.md` when they exist,
   only for the required specification revisions recorded in the plan's `Implementation Record` and the review's
   `Fix Report`. Treat each one as part of the request, not as a confirmed decision, and skip one that the
   specification already satisfies.

## Model and assess the request

Normalize actors, goals, workflows, entities, identity, relationships, lifecycle states, rules, inputs, outputs,
integrations, failures, exclusions, dependencies, and observable completion evidence. Use one canonical term per
concept; add a glossary only when source synonyms would otherwise confuse readers.

Internally assess each applicable area as `Clear`, `Partial`, or `Missing`:

- functional scope, success criteria, exclusions, and role differences;
- entities, attributes, relationships, identity, lifecycle, volume, and scale;
- performance, reliability, observability, security, privacy, and compliance;
- integrations, formats, protocols, versions, and dependency failures;
- negative cases, throttling, conflicts, concurrency, and recovery;
- technical constraints, tradeoffs, rejected alternatives, and completion signals.

Record why an area is irrelevant. Also detect synonym drift, unresolved TODOs, contradictions, and vague adjectives.

## Resolve material ambiguity

Use the shared [clarification dialogue guidelines](../../clarification-guidelines.md). Update the task model after each
answer and do not write until the dialogue and the assumption checkpoint end. If no question is necessary, proceed
directly to the checkpoint.

Give every applied default an ID (`A-001`, `A-002`, and so on), its basis, and the impact if it is wrong. The basis
is a source statement, a repository-relative path, or a named convention. Treat a default without a basis as a
question, not an assumption.

After the dialogue and before writing, present the assumptions once, in a single message, as a table of ID,
assumption, basis, and impact if wrong. Ask the user to reply `ok` or to correct entries by ID, for example
`A-003: admins only`. Apply each correction as an accepted answer and drop that assumption. The checkpoint is not
a numbered question; skip it when there are no assumptions.

Record the remaining assumptions, with their IDs, bases, and impacts, under `Assumptions`. Record accepted answers
and checkpoint corrections under `Clarifications`. Use `[NEEDS CLARIFICATION: <question>]` for every material
decision that is still unresolved when the dialogue ends; never downgrade one to an assumption, and never retain a
marker for an answered question. A specification that contains a marker is incomplete.

## Draft the specification

Use this structure, omitting only sections that are genuinely irrelevant:

```markdown
# Specification: <concise title>

Source request: <concise prose summary>
Revision: <n>

## Overview
## Current Behavior
## User Stories and Actors
## Scope
### In Scope
### Out of Scope
## Domain and Data Model
## Functional Requirements
## Edge Cases and Failure Handling
## Quality Attributes
## Integrations and Dependencies
## Constraints and Tradeoffs
## Assumptions
## Clarifications
## Success Criteria
## Acceptance Scenarios
## Glossary
```

Apply these rules:

- Set `Revision: 1` in a new specification. Increment it by one each time a revision changes the file. Treat an
  existing specification without the line as revision 1.
- Under `Current Behavior`, state only the existing behavior that the task changes or depends on, each statement with
  a repository-relative path as evidence. Describe what exists, not how to change it. Omit the section when the task
  touches no existing behavior.
- Number requirements `FR-001`, `FR-002`, and so on; success criteria `SC-001`, `SC-002`, and so on; and acceptance
  scenarios `AS-001`, `AS-002`, and so on. When revising, keep existing IDs and give each new item the next unused
  number.
- Make each requirement atomic, observable, unambiguous, and testable. Include actor, trigger or precondition,
  behavior, and observable result when relevant.
- Use `MUST`, `SHOULD`, and `MAY` consistently; reserve `MUST` for acceptance-critical behavior.
- Separate behavior from quality attributes and implementation suggestions. Describe the domain without prescribing
  tables, classes, or framework components unless the source requires them.
- Cover relevant validation, empty states, permissions, dependency failures, retries, idempotency, concurrency,
  conflicts, and recovery.
- State out-of-scope boundaries. Label inferred low-risk exclusions as assumptions.
- Replace vague quality claims with observable behavior or thresholds. Ask for a material threshold that the source
  does not state.
- Make success criteria measurable and technology-agnostic. Include qualitative outcomes only when they are
  observable.
- Add Given/When/Then scenarios for acceptance-critical workflows and material negative paths. Trace them to
  requirements and omit scenarios that only repeat another statement.
- Omit empty `Assumptions` and `Clarifications` sections. Leave no generic TODOs, placeholders, duplication, or
  contradictions.

## Validate, write, and report

Reassess coverage and confirm:

- every source goal maps to a requirement and success criterion;
- every `MUST` maps to a verifiable scenario or criterion;
- terminology, actors, entities, states, failures, and boundaries are consistent;
- implementation detail appears only when imposed as a constraint; and
- each remaining gap is excluded, recorded as an assumption with a basis, or represented by a marker.

Resolve validation failures in memory, then write exactly one target file. Read it once to verify the path, source
request, marker count, structure, and numbering. Do not run tests or formatters for this documentation-only workflow.

Open the report with one line stating whether the specification is complete. When any marker remains, state that the
specification is incomplete and not ready for implementation, and list the open questions.

Then report the target path; revision; scope; requirement, criterion, and scenario counts; incorporated assumptions,
clarifications, and revision requests; and any material coverage gaps.
