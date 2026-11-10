# Clarification dialogue guidelines

Apply this shared protocol when a workflow must resolve a material ambiguity with user input. Keep the workflow's
role-specific assumption, artifact, and blocking rules in effect.

## Select and prioritize questions

Apply these rules in order:

1. Prefer explicit source information, decisions already confirmed for the task, repository evidence, and established
   project conventions. A decision they settle is a fact; do not ask about it or record it as an assumption.
2. Ask when several reasonable interpretations have materially different implications for scope, correctness,
   architecture, data modeling, security or privacy, integration behavior, task decomposition, test design, operational
   readiness, compliance validation, or user-visible acceptance. A credible default does not remove the question;
   offer it as the recommended option instead of applying it silently.
3. Apply a default without asking only when the decision is low-impact and reversible, so that a wrong choice would
   neither change acceptance behavior nor cause rework beyond a local edit. Record it as an assumption, with its
   basis, in the artifact the workflow is allowed to write.
4. Prioritize by scope, user experience, security and privacy, then technical detail. Within that order, rank
   candidates by `impact × uncertainty`.
5. Balance areas. Do not spend two questions on low-impact details while a higher-impact area remains unresolved.
6. Do not ask about stylistic preferences, trivial details, matters the source or the repository already answers, or
   execution choices that do not block correctness.

If no candidate survives these rules, tell the user that no critical ambiguities were found and continue without a
dialogue.

## Manage the session

- Maintain the question queue internally. Reveal its estimated size, but not the content of later questions.
- Ask exactly one new question per assistant turn.
- Do not cap the number of questions. Continue until every material decision is resolved.
- Increment the question number only when first presenting a new question. Corrections or disambiguation for the
  same question do not increment it.
- After each valid answer, update the task model, reprioritize the remaining queue, and update the estimated total.
  Stop as soon as the material decisions are sufficiently resolved.
- End the dialogue when the material ambiguities are resolved or the user says `done`, `good`, or `no more`.
- Never turn a material decision into an assumption because the user ended the dialogue first. Leave it unresolved
  under the workflow's blocking rules.

## Ask a question

Start every question with `**Question <n> of about <total>:**`, where `<n>` is the question's position in the session
and `<total>` is the current estimate of all questions, for example `**Question 3 of about 7:**`. Follow it with a
self-contained interrogative ending in `?`. Immediately add a plain-language sentence beginning with
`Why it matters:` that explains the delivery or acceptance impact.

Use multiple choice when 2–5 distinct, mutually exclusive options exist:

```markdown
**Question <n> of about <total>:** <self-contained question ending in ?>
Why it matters: <one sentence describing the delivery or acceptance impact.>

**Recommended:** Option <letter> - <one or two sentences of reasoning>

| Option | Description |
|---|---|
| A | ... |
| B | ... |
| C | ... |
| Short | Provide a different short answer (<=20 words) |

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or
provide your own short answer.
```

Recommend the option best aligned with confirmed requirements, existing project patterns, maintainability, and risk
reduction. Include the `Short` row only when a free-form alternative is appropriate.

Use a constrained short answer when discrete choices would not be useful:

```markdown
**Question <n> of about <total>:** <self-contained question ending in ?>
Why it matters: <one sentence describing the delivery or acceptance impact.>

**Suggested:** <proposed answer> - <brief reasoning>

Format: Short answer (<=20 words). You can accept the suggestion by saying "yes" or "suggested", or provide your own
answer.
```

## Process the response

- For multiple choice, interpret `yes` or `recommended` as accepting the immediately preceding recommendation.
  Otherwise require a listed option letter or, when `Short` is present, an alternative of at most 20 words.
- For a short answer, interpret `yes` or `suggested` as accepting the immediately preceding suggestion. Otherwise
  require an answer of at most 20 words.
- If a reply is ambiguous or invalid, request a brief correction as part of the same question. Do not increment the
  question number or advance the queue.
- Record every valid answer in the workflow's permitted working memory or artifact.
