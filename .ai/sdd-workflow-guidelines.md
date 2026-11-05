# SDD workflow guidelines

Apply these shared rules when an artifact-based SDD skill selects a task or inspects a working tree. The invoking
skill defines its allowed artifact directories, required artifact types, write permissions, and stopping conditions.

## Name task artifacts

Tasks have no external identifier. A task slug, derived from the task's prose description, names its artifacts:
`.ai/specs/spec-<task-slug>.md` and `.ai/plans/plan-<task-slug>.md`.

- Derive the slug from the prose: use 2-6 descriptive lowercase ASCII words joined by hyphens, keep only letters,
  digits, and hyphens, and limit it to 64 characters.
- When the target path already holds an artifact for another feature, extend the slug until it is unique. Never
  overwrite an artifact for another feature.
- Put a `Source request: <concise prose summary>` line right after the title of every specification and plan. Keep
  the summary specific enough to identify the feature in a later session.

## Select task artifacts

1. Accept a task slug, an allowed artifact basename, or a repository-relative path in an allowed artifact directory.
2. For a task slug, require the supplied value to equal its trimmed form and to satisfy the slug format above. Reject
   any other value and request a valid task slug.
3. Resolve a basename only by exact filename. Normalize a supplied path and require its target to remain inside an
   allowed artifact directory. Reject absolute paths, traversal, and paths elsewhere.
4. If a supplied identifier has no exact match, stop and report it. Do not choose a substitute.
5. When discovering specifications or plans, include files even when Git ignores them. Use a directory listing or
   search mode that does not apply ignore rules.
6. If no identifier is supplied, group available artifacts by task slug — the artifact basename without `.md` and
   without one leading `spec-` or `plan-`. When the request describes the feature in prose, read the opening
   `Source request` line of each candidate and treat a match only as a candidate signal; never match on the file name
   alone. Select the task only when exactly one valid candidate remains; otherwise ask the user to identify it before
   writing or reviewing code.
7. Read every selected artifact completely. Treat the specification as the acceptance authority and a compatible plan
   only as technical guidance.

## Inspect and preserve the working tree

Run inspection commands from the repository root. They require no running services or environment variables and
write only to the terminal.

1. Before writing or reviewing code, inspect `git status --short`, `git diff`, `git diff --staged`, and relevant
   untracked files in full.
2. Classify changes as task-related, confirmed unrelated, or ambiguous. Use the specification, selected plan, file
   content, and surrounding code as evidence; do not classify by filename alone.
3. Treat task-related changes as the workflow result. Preserve confirmed unrelated changes without including them in
   the task verdict. Include ambiguous behavior-affecting changes in the inspection set, preserve their ambiguous
   classification, and report their uncertain scope.
4. If task work overlaps a pre-existing change that cannot be preserved safely, stop and ask how to proceed.
5. Record the initial state internally when later edits or formatting could make attribution unclear. Report
   formatter side effects instead of silently treating them as intentional task changes.
6. Do not stage, commit, push, switch branches, stash, reset, revert, or otherwise change version-control state unless
   the user explicitly requests it.

## Use project memory

Search `.ai/memories/` for verified findings relevant to the selected task and read only matching entries. Do not load
the directory wholesale or treat an unverified memory as authority.
