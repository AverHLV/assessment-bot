# Agent guidelines

## Project brief

- Stack: Python 3.13, Django, discord.py, and PostgreSQL. Tests use Django's `unittest`-based test framework.
- The project and its associated services run in Docker containers assembled with Docker Compose.
- Never perform a fresh project setup. Always assume that the containers have been built and the project virtual
environment has been provisioned. Containers may be stopped; use `make container@start` before commands that require
running services.
- Run project workflows through the Makefile from the repository root. Use these canonical commands:
  - `make container@start` — start the containers.
  - `make container@stop` — stop the containers.
  - `make container@restart` — restart the containers.
  - `make container@console` — open a shell in the application container.
  - `make container@logs` — follow container logs.
  - `make project@test` — run the test suite.
  - `make project@format` — lint and format the code.
- In particular, `make container@console` and `make project@format` require the application container to be running.
`make project@test` starts the required containers through its Makefile prerequisite.
- The Python executable inside the application container is `/opt/venv/app-4PlAip0Q/bin/python`. Always use this
virtual environment. Do not use the system Python, a system virtual environment, or any other environment.
- The project uses `uv` for package management. Never use another package manager. Do not add or update dependencies;
new dependencies are added by a developer.
- Treat `pyproject.toml` and `uv.lock` as the dependency sources of truth, `Dockerfile` as the runtime source,
`docker-compose.yaml` as the service topology, `.env.example` as the supported environment-variable reference, and
`Makefile` as the command interface. This guide only summarizes them; do not duplicate their values elsewhere.

## Shared conventions

- Keep every generated or edited Markdown file within 120 characters per line. Wrap prose at that limit instead of
writing a paragraph on a single line. Do not reflow content where a line break would change meaning or break parsing,
such as inside fenced code blocks, table rows, long URLs, or front-matter values. Leave such lines intact even when
they exceed the limit.

## Instructions reproducibility

- Write instructions so they can be reproduced on another machine.
- Use repository-relative paths and commands that run from the repository root.
- Do not include home directories, usernames, unexplained local ports, or commands that exist only on one developer's
machine.
- Prefer repository-provided wrappers such as the Makefile targets above. Use a tool name or a documented environment
variable instead of a machine-specific absolute path.
- The designated container interpreter is an explicit project requirement and the only allowed absolute SDK path.
- For every non-trivial command, document its working directory, required services, required environment variables,
expected input data, and output location.

## Skill routing

- Use `spec-writer` when a task needs a new or revised specification. It requires a prose task description and edits
  only `.ai/specs/`.
- Use `implementer` when a readable specification exists and production work is requested. It implements small tasks
  directly or writes a plan and stops for large or materially uncertain tasks; it never writes tests.
- Use `test-writer` after task-related production changes exist and tests must be written or run. It intentionally
  edits only tests and test-support code.
- Use `verifier` after implementation and tests exist and a static audit is requested. It edits nothing and executes
  no project code.
- Do not use a later-stage skill to supply a missing prerequisite; route the task to the earlier applicable skill.

## Skill conventions

- Write skills as agent-agnostic instructions by default. Do not mention an agent product, agent-specific capability,
model, or vendor-specific behavior unless the skill is explicitly declared to be for that agent only.
- Store every project skill in the canonical `.ai/skills/<skill-name>/` directory.
- Whenever a skill is created or updated, check its discovery links in both `.agents/skills/` and
`.claude/skills/`. Create or repair relative symlinks so both locations resolve to the canonical skill:
  - `.agents/skills/<skill-name> -> ../../.ai/skills/<skill-name>`
  - `.claude/skills/<skill-name> -> ../../.ai/skills/<skill-name>`
- Verify each symlink resolves to the canonical skill directory.

## Agent memory conventions

- Store project memory in `.ai/memories/`.
- Record only verified findings that are likely to help with similar future tasks, such as non-obvious library behavior,
discrepancies with official documentation, reliable workarounds, or reproducible complex bugs.
- Each memory entry must include:
  - the conditions under which the behavior occurs;
  - the minimal reproduction steps;
  - the actual result and a verified workaround;
  - the component versions to which the finding applies;
  - a criterion for reviewing or removing the entry.
- Do not store task histories, unverified assumptions, personal paths, secrets, or information already documented
unambiguously in current project documentation.

## Agent tool conventions

- Store reusable agent scripts and utilities in `.ai/tools/`.
- When the same shell command or parser has been assembled for a second time, consider turning it into a small
repository-provided tool.
- Use agent tools for repeatable tasks such as preparing fixtures, extracting context from complex documents,
checking configuration, collecting diagnostic bundles, or validating artifacts.
- Make tools reproducible: invoke them from the repository root with repository-relative paths and document their
prerequisites, inputs, and outputs.
