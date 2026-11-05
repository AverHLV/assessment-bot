# Test-writing guidelines

Apply these project-wide rules when writing or reviewing tests.

## Files and classes

- Do not write tests for migrations. `core/tests.py` already fails when model changes lack a migration.
- Place tests in the `tests` package of the package that owns the module under test. Include `__init__.py` in every
  `tests` package.
- Derive the test filename from the module under test and its path inside that package. For example,
  `bot/views/assessment_rate.py` is covered by `bot/tests/test_views_assessment_rate.py`.
- Add a concise behavior or entity suffix when one module needs multiple test files.
- Split test modules longer than 300 lines into focused modules with names that describe the behavior or entity tested.
- Organize every test case in a `django.test.TestCase` subclass, or a `SimpleTestCase` subclass when the tested code
  never touches the database. Do not write standalone test functions.
- Group classes by command, view, modal, model, client, or cohesive behavior, following the nearest established
  layout.
- Keep reusable assertion helpers and base test cases separate from concrete test-case classes. Reuse an existing one
  when suitable; otherwise add it to dedicated test-support code such as the package's `tests/base.py`.

## Test support

Read and reuse this support before introducing new helpers:

- `core/utils_tests.py` provides the project `TestRunner`, configured as `TEST_RUNNER`, which disables logging and
  Sentry and uses a fast password hasher, and the helpers `get_httpx_test_response`, `get_log_record`, and
  `pause_date_auto_fields`.
- `bot/tests/base.py` provides `CogBaseTestCase`, with mocked `interaction` and `bot`, the cog under test, a mocked
  thinking task, `assert_thinking`, and `assert_thinking_with_loop`; `CogWithCommandsBaseTestCase`, which adds
  `self.user` and binds it to the interaction; `PaginatorBaseTestCase`; and the asynchronous mock helpers
  `AsyncTestContextManager`, `get_async_context_manager_mock`, and `get_async_iterator_mock`.
- An app's `tests/factories.py` holds its `factory_boy` model factories, such as `UserFactory` in
  `api/user/tests/factories.py` and `MediaFactory`, `AssessmentFactory`, `PollFactory`, and `VoteFactory` in
  `api/assessment/tests/factories.py`.

## Test isolation and external boundaries

- Keep tests isolated from live external dependencies. Do not create or require tests, validation checks, or review
  recommendations that depend on external API calls, live agents or models, production accounts or credentials,
  paid services, or provider availability.
- Replace external boundaries with deterministic mocks or fakes. Control successful responses, errors, timeouts,
  and malformed responses so the application's required paths remain reproducible.
- The external boundaries are the Discord API, represented by the mocked interaction and bot, and the HTTP clients
  in `core/clients.py` and their subclasses. Patch the client method or the module-level call used by the code under
  test, and build HTTP responses with `get_httpx_test_response`.
- Preserve integration coverage of project-owned behavior using the real handlers, forms, models, and the isolated
  test database. External isolation does not require mocking application persistence or other project-owned logic.
- For agent or model integrations, verify contract wiring, supplied context and evidence, tool availability and
  authorization, persisted results, and handling of controlled responses and failures. Scripted responses verify
  application handling; they do not prove live model judgment.
- Do not require live agent or model evaluations for test coverage, conformance verdicts, or review gates. Report
  missing isolated checks of project-owned behavior rather than missing checks of a live external dependency.

## Test stability

- Do not add tests whose expected outcome depends on uncontrolled scheduling, guessed sleeps, elapsed wall-clock
  time, or real deadlines. Do not mask that dependency with retries, longer waits, or repeated runs until a pass.
- Concurrent execution is allowed when events, barriers, or controlled fakes establish the required interleaving,
  or assertions remain valid regardless of execution order after all tasks complete. Reuse existing deterministic
  concurrency helpers and patterns when extending tests; `asyncio.gather` alone is not evidence of instability.
- A generous timeout may guard against a hung test, but must not establish ordering or trigger the behavior under
  test. Expiry of the guard must fail the test, never count as successful coverage of application timeout handling.
- Exercise race and timeout handling through deterministic preconditions, controlled interleavings, injected or
  patched clock functions, or injected failures. Examples include pre-creating the row that wins a race, making
  a collaborator raise `IntegrityError` or `TimeoutException`, and patching `asyncio.sleep`. Control the trigger while
  exercising the application's actual handling.
- Omit a specific rare race or timing-sensitive scenario only after inspecting existing helpers and ruling out
  applicable deterministic approaches with concrete code evidence or attempt results. Prefer that narrow gap to
  a flaky test. Calling a scenario "timing-sensitive" or noting that it uses concurrent code is not sufficient.
- This exception applies only to the identified scenario that cannot be covered deterministically. Keep coverage
  of deterministically testable behavior, including required negative paths and surrounding acceptance workflows.
  An omission does not waive an implementation requirement and must remain identified as uncovered.

## Style and integration boundary

- Use `match`/`case` instead of large `if`/`elif`/`else` chains that dispatch on the same value or structure. Keep
  `if` statements for unrelated conditions that do not naturally fit pattern matching.
- Add a blank line after a docstring when code follows it in the same scope.
- Separate substantial logical blocks with a blank line, including loops and `if` statements, and the code around
  them.
- Do not insert blank lines between the branches of a single `if`/`elif`/`else` chain, unless its branches are
  large standalone blocks where blank lines between them improve readability.
- Within each test, separate setup, execution, and assertions with blank lines, and separate distinct logical blocks
  within those phases when it improves readability.
- Assert the project's own behavior. Do not write a test whose only assertion is that a dependency works as
  documented; do cover dependency behavior that project code configures or exposes as part of its contract. This
  does not permit omitting a required negative path; see "Assertions and query counts".
- Prefer integration tests. Exercise Discord handlers with the mocked interaction, the real cog, view, modal, form,
  and model code, and the test database. Call an app command through
  `self.cog.<command>.callback(self.cog, self.interaction)`, and call view item callbacks and modal `on_submit`
  directly. Exercise management commands through `handle_async` or `call_command`, and HTTP or admin views through the
  Django test client. Mock only external boundaries or deliberately isolated services.
- Treat a Discord handler, a management command, or an HTTP view as the widest permitted integration boundary. Use
  unit tests only for large isolated logic that handler-level coverage cannot exercise or diagnose; unit tests
  supplement handler integration coverage.
- Use `async def` test methods when the tested interface requires awaiting; Django runs them. Use `def` for
  synchronous code. When an asynchronous test method has `patch` decorators, place `@async_to_sync` directly below
  them, as the existing tests do.
- Create records shared by the tests of a class in `setUpTestData`, and per-test state in `setUp`.
- In asynchronous tests, wrap synchronous factory calls with `sync_to_async`, and read database state with the
  asynchronous ORM API.

## Users and interactions

- Inherit `CogWithCommandsBaseTestCase` for handlers that resolve the interacting user, instead of building users and
  interaction identities manually.
- Pass the test user to views and modals that are bound to a user.
- Cover the first-interaction path, where `BaseCog.get_user` creates the user, when the changed behavior depends on
  it.
- Authenticate HTTP or admin views with `self.client.force_login(user)`, and cover the unauthenticated case by
  calling the view without logging in.

## Names, URLs, and data

- Name a positive test `test__<entity_name>__<slug_of_what_is_tested>`. Omit the final slug only when one integration
  test fully describes the entity and no useful distinction exists.
- Name a negative test `test__<entity_name>__errors__<slug_of_what_is_tested>`.
- Use concise snake-case names that describe observable behavior rather than implementation mechanics.
- Resolve HTTP URLs with `django.urls.reverse(...)`; do not hard-code paths.
- Move large or shared setup into `setUpTestData`, `setUp`, or a helper. Keep scenario-specific setup in the test.
- Define a hardcoded value used more than once, such as a string or an integer, as a test-case class attribute or as
  a module-level constant in the module that needs it the most, and reuse it.
- Keep an expected assertion value as a literal when sharing a constant between the input and the assertion would
  make the test pass regardless of the tested behavior.
- Assert user-facing texts through the `message_*` attributes of the tested cog, view, or modal.
- Create database records only through the factories in the owning app's `tests/factories.py`.
- Add a missing factory as a `factory.django.DjangoModelFactory` subclass instead of constructing a model directly in
  a test. Use `pause_date_auto_fields` when a test must control an `auto_now` or `auto_now_add` field.
- Use mocks for external boundaries and nondeterministic collaborators, not as substitutes for integration coverage.

## Assertions and query counts

- Use `self.assertNumQueries` whenever the tested execution can issue database queries, including negative paths that
  reach the database. Wrap only the measured execution and assert the exact expected count.
- Take the expected count from the query budget in the selected plan or implementer report when one is available.
  Otherwise build the budget from the code path as defined in the
  [implementation guidelines](implementation-guidelines.md). Never adopt a measured count without checking each
  captured statement against the query efficiency rules there.
- Do not loosen a query count to accommodate inefficient behavior. Report an unjustified repeated load, a per-row
  query or write, a count above the budget, or any other meaningful unexpected count as an implementation failure.
- Assert results in this order, omitting only inapplicable steps:
  1. immediate public result, such as the interaction response content, embed, and view, a return value, or an HTTP
     status code and body;
  2. persistent database or model state;
  3. external mock calls and non-calls, including important arguments.
- Move large or shared response, database-state, and mock assertions into focused helpers or base test cases.
- For every tested handler, cover user binding, validation, empty states, and each handler-specific error response
  required by the specification or reachable changed behavior, including `on_error` handling. Do not omit a negative
  path merely because a shared base class implements it.
