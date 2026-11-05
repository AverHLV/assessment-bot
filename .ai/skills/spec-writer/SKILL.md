---
name: spec-writer
description: >-
  Create or revise a testable SDD specification from a task description. Use when an informal request, user
  stories, documentation, constraints, or related context must become a solution-neutral artifact under `.ai/specs/`
  without changing implementation files.
---

# Spec Writer

Create an implementation-ready, technology-aware but solution-neutral specification. Ask only questions that can
prevent material rework; document reasonable assumptions for everything else.

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
4. When revising, keep the existing filename and update its `Source request` line only when the scope changes. Do not
   discard confirmed content or restructure it merely to fit a template. Ask which source governs before replacing a
   confirmed decision.

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
answer and do not write until the dialogue ends. If no question is necessary, proceed directly.

Record applied defaults under `Assumptions` and accepted answers under `Clarifications`. Use
`[NEEDS CLARIFICATION: <question>]` only for an unresolved decision with no safe default. Keep at most the three
highest-impact markers and never retain a marker for an answered question.

## Draft the specification

Use this structure, omitting only sections that are genuinely irrelevant:

```markdown
# Specification: <concise title>

Source request: <concise prose summary>

## Overview
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

- Number requirements `FR-001`, `FR-002`, and so on; number success criteria `SC-001`, `SC-002`, and so on.
- Make each requirement atomic, observable, unambiguous, and testable. Include actor, trigger or precondition,
  behavior, and observable result when relevant.
- Use `MUST`, `SHOULD`, and `MAY` consistently; reserve `MUST` for acceptance-critical behavior.
- Separate behavior from quality attributes and implementation suggestions. Describe the domain without prescribing
  tables, classes, or framework components unless the source requires them.
- Cover relevant validation, empty states, permissions, dependency failures, retries, idempotency, concurrency,
  conflicts, and recovery.
- State out-of-scope boundaries. Label inferred low-risk exclusions as assumptions.
- Replace vague quality claims with observable behavior or thresholds. Ask when a material threshold has no safe
  default.
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
- each remaining gap is excluded, safely assumed, or represented by an allowed marker.

Resolve validation failures in memory, then write exactly one target file. Read it once to verify the path, source
request, marker count, structure, and numbering. Do not run tests or formatters for this documentation-only workflow.

Report the target path; scope; requirement and criterion counts; incorporated assumptions and clarifications; and any
remaining markers or material coverage gaps.
