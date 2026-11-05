# Implementation guidelines

Apply these project-wide rules when implementing or reviewing production changes.

## Architecture and dependencies

- Follow the existing repository layout: domain Django apps under `api/` (models, managers, admin, HTTP clients,
  migrations), the Discord bot app under `bot/` (cogs in `bot/commands/`, views in `bot/views/`, modals in
  `bot/modals/`, forms in `bot/forms.py`, management commands in `bot/management/commands/`), and shared
  infrastructure, settings, and base models in `core/`.
- Use only dependencies already declared in `pyproject.toml` and `uv.lock`. Do not add or update dependencies.
- Always analyze built-in and already-declared dependency-provided functionality before implementing a feature. Use
  the available functionality instead of duplicating it in the project.
- Put reusable query filters in the custom `QuerySet` or manager classes in the owning app's `managers.py`, and
  attach them to the model as the existing models do.
- Build external HTTP integrations on `AsyncHTTPBaseClient` or `AsyncHTTPTokenAuthBaseClient` from
  `core/clients.py`, and expose the shared client instance from the owning app's `__init__.py`.
- Use raw SQL only when the ORM cannot express the operation reasonably. Do not put application business logic in
  database triggers or custom database functions.

## Simplicity and scope

- Keep code small, straightforward, and easy to read. Prefer clear control flow and descriptive names over cleverness,
  dense expressions, or unnecessary decomposition.
- Split production modules longer than 200 lines into focused modules with descriptive names. Exclude
  `core/settings.py` and migration modules under `<app>/migrations/` from this limit. Keep application settings
  together in `core/settings.py` regardless of its length.
- Use `match`/`case` instead of large `if`/`elif`/`else` chains that dispatch on the same value or structure. Keep
  `if` statements for unrelated conditions that do not naturally fit pattern matching.
- Prefer direct use of established project layers over introducing new wrappers, services, factories, base classes,
  or protocols. Add an abstraction only when it serves multiple concrete uses, isolates a meaningful external
  boundary, or is required by a pattern already established in this project.
- Keep logic close to the layer that owns it. A pass-through layer is not useful unless it adds policy, validation,
  transaction handling, reuse, or another identifiable responsibility.
- Do not leave indirection or flexibility that cannot be traced to a specification requirement, an existing
  convention, or a current concrete use.

## Formatting

- Add a blank line after a docstring when code follows it in the same scope.
- Separate substantial logical blocks with a blank line, including loops and `if` statements, and the code around
  them.
- Do not insert blank lines between the branches of a single `if`/`elif`/`else` chain, unless its branches are
  large standalone blocks where blank lines between them improve readability.

## Logging and exceptions

- Inside an exception handler, log the exception with `logger.exception` rather than `logger.error`, and log the
  exception context rather than the exception object alone, so both the message and the traceback are recorded.
  Include the exception message in the log message, for example `logger.exception(f'Operation failed: {exc}')`.
- Outside an active exception handler, or when logging an exception other than the one being handled, pass the
  exception explicitly with `exc_info=<exception>`. `logger.exception` alone records no traceback there.

## Constants

- Define a hardcoded value used more than once, such as a string or a regular expression, as a module-level constant
  in the module that owns the value's concept, and import it everywhere else it is reused.
- Do not introduce a shared constants module for values used by a single package.

## Models, queries, and migrations

- Keep model-related enums on the model class as `models.TextChoices` or `models.IntegerChoices`, and pass them to the
  field's `choices`.
- Give every foreign key an explicit `on_delete` and `related_name`, and give every concrete model a useful `__str__`.
- Reuse the abstract base models in `core/models.py`, such as `TimeStamped` and `Directory`, where they fit.
- Keep small model-local state transitions and derived-field behavior on the model.
- Save changed fields of an existing instance with `update_fields`.
- Put new migrations in the owning app's `migrations/` package. Never modify an unrelated or historical migration.
- Review generated migrations for constraints, indexes, nullable and default behavior, data transitions, locking,
  reversibility, and compatibility with the model state.

## Asynchronous code

- Bot handlers are asynchronous. Use the asynchronous ORM API, such as `aget`, `afirst`, `acount`, `aexists`,
  `asave`, `aupdate`, and `async for` over a queryset, instead of synchronous queryset evaluation.
- Load every related object an asynchronous path will access in the original query with `select_related` or
  `prefetch_related`. Lazy loading in asynchronous code raises `SynchronousOnlyOperation`.
- Wrap only operations that have no asynchronous API, such as form validation, with `sync_to_async`.
- Keep blocking I/O and CPU-heavy work out of asynchronous handlers. Use the asynchronous HTTP clients for external
  calls.

## Query efficiency

- Select only the fields needed by the caller with `only()`, `values()`, or `values_list()`, and paginate collections
  where applicable.
- Load each row at most once within one interaction or transaction. Pass the loaded object, or the fields it provides,
  to every later step instead of selecting it again in a cog, view, modal, form, helper, or model method.
- Read a row again only when the earlier copy cannot be trusted: to take a row lock with `select_for_update()`, or to
  see current state after a commit, a new transaction, or an external call or `await` during which other workers may
  have changed it. Keep such rereads and their fencing checks, such as ownership, status, or claim token checks; never
  replace them with the earlier object.
- Fetch related or derived data for a selected collection with one bulk query, `select_related`, `prefetch_related`,
  `Prefetch`, or an annotation. Never issue one query per collection item.
- Insert or update a set of rows with one bulk statement, such as `bulk_create`, `bulk_update`, or
  `QuerySet.update()`. Never write them one by one in a loop.

Common redundant patterns and their fixes:

| Redundant pattern | Fix |
|---|---|
| `BaseCog.get_user` loads the current user, and a view, modal, or helper selects the same user again by ID. | Pass the loaded user object on. |
| A helper receives an ID and selects the row although its caller already holds the loaded object. | Change the helper to accept the object or the fields it needs. |
| A loop over selected rows runs one query per row to attach a new attribute, such as a count or a latest child. | Annotate the original queryset, or select the attribute for all row IDs in one grouped query and attach it in memory. |
| A loop accesses an unloaded foreign key or reverse relation of each selected row. | Load it in the original query with `select_related`, `prefetch_related`, or `Prefetch`. |
| A loop calls `save()` or `create()` for each row. | Use one `QuerySet.update()`, `bulk_update`, or `bulk_create`. |
| Code calls `refresh_from_db()` right after writing a row only to get generated values. | Use the values Django already sets on the instance after `save()` or `bulk_create()` on PostgreSQL. |
| Code evaluates a queryset or calls `count()` only to check whether rows exist. | Use `exists()` or `aexists()`. |

## Query budget

- For every changed execution path, including each negative path that reaches the database, record a query budget:
  every SQL statement in execution order, with its purpose. Include statements issued by `BaseCog.get_user`,
  `get_or_create`, form validation such as unique checks, signals, `refresh_from_db`, and lazy loading.
- Every entry must read or write data that no earlier entry of the same path already provides, unless it is a
  justified reread from the query efficiency rules; name the lock or freshness reason as its purpose.
- Keep necessary transaction-control statements in the budget, such as `SAVEPOINT` and `RELEASE SAVEPOINT` emitted by
  a nested `transaction.atomic()` block, including the one inside the create path of `get_or_create`. `TestCase` wraps
  every test in a transaction, so `assertNumQueries` counts them. Name the failure each savepoint isolates as its
  purpose. Remove a savepoint that isolates nothing the path recovers from.
- No entry may repeat once per processed row. An entry may repeat once per fixed-size batch, such as `bulk_create` or
  `bulk_update` with `batch_size`, or `iterator(chunk_size=...)` combined with `prefetch_related`; record the batch
  size. Remove or merge every entry that fails these checks.
- The budget total is the expected count for `assertNumQueries` in tests of that path. When batching makes the count
  depend on input size, state the budget for the input size the test uses.

## Discord commands, views, and modals

- Add app commands as methods of a `BaseCog` subclass in `bot/commands/` with the `command` decorator and a
  `description`, and register new cogs where the existing cogs are registered.
- Build interactive components on the base classes in `bot/views/base.py` and `bot/modals/base.py`, so error
  handling, pagination, and form handling stay consistent.
- Resolve the interacting Discord user with `BaseCog.get_user`. Bind views and modals that act for a user to that user.
- Validate user input with Django forms in `bot/forms.py`, as `BaseCreateModal` does.
- Keep user-facing texts as `message_*` class attributes of the cog, view, or modal that sends them.
- Show the thinking indicator through `thinking.show_thinking` or `thinking.start_task` before database or external
  work, following the existing handlers.
- Keep the main feature flow in the handler. Use model methods, querysets, forms, and established helpers for data
  access and shared concerns.
- Preserve the existing user binding, validation, error message, cooldown, and compatibility contracts unless the
  specification explicitly changes them.
