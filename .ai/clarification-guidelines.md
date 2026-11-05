# Clarification dialogue guidelines

Apply this shared protocol when a workflow must resolve a material ambiguity with user input. Keep the workflow's
role-specific assumption, artifact, and blocking rules in effect.

## Select and prioritize questions

Apply these rules in order:

1. Prefer explicit source information, decisions already confirmed for the task, and established project conventions.
2. Apply a common project or industry default when one is low-risk and reversible. Record it as an assumption in the
   artifact the workflow is allowed to write.
3. Ask only when several reasonable interpretations have materially different implications for scope, correctness,
   architecture, data modeling, security or privacy, integration behavior, task decomposition, test design, operational
   readiness, compliance validation, or user-visible acceptance, and no safe default exists.
4. Prioritize by scope, user experience, security and privacy, then technical detail. Within that order, rank
   candidates by `impact × uncertainty`.
5. Balance areas. Do not spend two questions on low-impact details while a higher-impact area remains unresolved.
6. Do not ask about stylistic preferences, trivial details, matters the source already answers, or execution choices
   that do not block correctness.

If no candidate survives these rules, tell the user that no critical ambiguities were found and continue without a
dialogue.

## Manage the session

- Maintain the question queue internally and do not reveal later questions.
- Ask exactly one new question per assistant turn.
- Ask no more than five new questions during one workflow session.
- Increment the count only when first presenting a new question. Corrections or disambiguation for the same question
  do not increment it.
- After each valid answer, update the task model and reprioritize the remaining queue. Stop as soon as the material
  decisions are sufficiently resolved.
- End the dialogue when the material ambiguities are resolved, the user says `done`, `good`, or `no more`, or the fifth
  question is resolved.

## Ask a question

Start every question with `**Question:**` followed by a self-contained interrogative ending in `?`. Immediately add a
plain-language sentence beginning with `Why it matters:` that explains the delivery or acceptance impact.

Use multiple choice when 2–5 distinct, mutually exclusive options exist:

```markdown
**Question:** <self-contained question ending in ?>
Why it matters: <one sentence describing the delivery or acceptance impact.>

**Recommended:** Option <letter> - <one or two sentences of reasoning>

| Option | Description |
|---|---|
| A | ... |
| B | ... |
| C | ... |
| Short | Provide a different short answer (<=5 words) |

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or
provide your own short answer.
```

Recommend the option best aligned with confirmed requirements, existing project patterns, maintainability, and risk
reduction. Include the `Short` row only when a free-form alternative is appropriate.

Use a constrained short answer when discrete choices would not be useful:

```markdown
**Question:** <self-contained question ending in ?>
Why it matters: <one sentence describing the delivery or acceptance impact.>

**Suggested:** <proposed answer> - <brief reasoning>

Format: Short answer (<=5 words). You can accept the suggestion by saying "yes" or "suggested", or provide your own
answer.
```

## Process the response

- For multiple choice, interpret `yes` or `recommended` as accepting the immediately preceding recommendation.
  Otherwise require a listed option letter or, when `Short` is present, an alternative of at most five words.
- For a short answer, interpret `yes` or `suggested` as accepting the immediately preceding suggestion. Otherwise
  require an answer of at most five words.
- If a reply is ambiguous or invalid, request a brief correction as part of the same question. Do not increment the
  count or advance the queue.
- Record every valid answer in the workflow's permitted working memory or artifact.
