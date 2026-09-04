# Testing rules

Source: internal wiki pages "Guideline: Testing principles", "Pytest
guidelines" and "Test classification and architecture" (Max Linke, 2026),
"Guideline: Flaky Tests" (Anastasiia Shevchuk, 2026), the testing parts of the
"Engineering Manifesto" (Lars Michelsen, 2026) and of "All things Vue"
(Benedikt Seidl, Moritz Kirschner, 2026).

Untested code is unfinished and does not ship. Tests exist to catch
regressions, make refactoring safe, and act as the first user of an API. Ask
"how will we know this works?" before writing the first line; if the answer is
not obvious, that is a design conversation, not a CI problem. A good test is
expressive, fast, never flaky, and fails only when behavior is wrong, never
because an internal was renamed. Automated tests verify what you expected to go
wrong; before calling a change done, exercise the real workflow once to catch
what you did not think of.

**Behavior** is what a caller observes through the public interface: function
signatures, REST endpoints, CLI commands, exported packages. Test behavior, not
implementation.

## 1. Decide whether a test is warranted

Every test is code to maintain. More tests are not better.

- Write a test for: user-visible flows and contracts, branching logic, error
  and failure paths, module boundaries where a change on one side could
  silently break the other, areas with a regression history.
- Every bug fix ships with a regression test that fails without the fix. If a
  bug can happen twice, a test catches it the first time.
- Do not write a test for: trivial code, third-party library internals,
  behavior already covered by another test, excessive parameter variations of
  the same behavior.
- Verify each behavior once, at one level. If two tests cover the same
  behavior, delete the higher-level one.
- Doctests are executable documentation, not coverage. Never rely on one as the
  only test of any logic.

## 2. Test levels and where they live

| Level       | Scope                                                                                                                                                                                               | Setup allowed                                      | Location                                                                                                                                                                       | Runtime                            |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------- |
| Unit        | One function, method, or class of one package. Collaborators replaced by doubles only where necessary.                                                                                              | None. No running processes, no test-only services. | The package's `tests/` directory: `packages/<pkg>/tests/` or `non-free/packages/<pkg>/tests/`. For the not yet packaged `cmk/` tree: `tests/unit/`, mirroring the module path. | 1–10 ms per test                   |
| Component   | One package with its real package-level collaborators wired together. May run the package's own processes; nothing from another package, no site.                                                   | In-process fixtures.                               | Same `tests/` directory. Split into `tests/unit/` and `tests/component/` only when that helps.                                                                                 | < 30 s per test, suite < 10 min    |
| Integration | Two or more first-party packages, verifying a cross-package contract (agent controller ↔ agent receiver, check engine ↔ plugin API, REST endpoint ↔ framework). No site, no real monitored systems. | Mocks, sockets, lightweight in-process setups.     | `tests/integration/<feature>/` with its own Bazel target.                                                                                                                      | < 30 s per test, suite < 10 min    |
| System      | The whole system through its external interfaces: GUI via Playwright, REST API via HTTP client, one or more running sites, real monitored systems. Includes E2E and site tests.                     | Running site(s), browser automation, HTTP client.  | `tests/system/<feature>/`, run via `tests/run_tests.sh test-system-<suite>`.                                                                                                   | Suite < 30 min, critical path only |

- Package and integration tests are Bazel-managed and cached:
  `bazel test //packages/<pkg>/...`, `bazel test //tests/unit/<path>/...`,
  `bazel test //tests/integration/...`. Always run the tests of the packages
  you touched. Run integration tests when you touch a cross-package boundary.
  Run system tests locally only when working on the test itself or debugging a
  CI failure; otherwise rely on CI.
- Organize system tests by feature, not by fixture: `tests/system/redfish/`,
  not "everything that needs Playwright". The `singlesite`, `multisite`, `gui`,
  `gui_crawl`, `update`, and `plugins` directories are transitional holding
  areas. Do not add new suites there; prefer moving a test out into its
  feature directory.
- Single-site and multi-site tests (formerly "integration" and "composition")
  are the same kind of system test. E2E tests are system tests that almost
  always need a site.
- Package and integration tests mirror the source layout: one test module per
  source module, grouped by package, moving with the code. System and
  acceptance tests are organized by feature or workflow and never tied to
  internal APIs.
- Acceptance tests live under an `acceptance/` path segment. Changing their
  expected outcome requires explicit stakeholder alignment; never adjust one to
  make your change pass.
- Performance tests live in `tests/performance/` and need guaranteed
  resources, so CI selects them by tag.
- Exceeding a runtime budget is a design signal, not a reason to raise the
  budget.

## 3. Pick the level by behavior, not habit

First state the behavior in one sentence a non-engineer could understand. Then
choose the lowest level that can verify it honestly: low enough to pinpoint the
failure, high enough to survive a restructure.

- Default: the public interface of a single component. Python API → unit test
  against that API. Web server or CLI → the running process via its REST
  endpoints or command line.
- Unit and component tests carry internal logic. Testing internal classes
  directly gives less confidence than testing the component's public surface.
- System tests only for critical user paths that span several components,
  cross-cutting features, and visual regression. They are slow, costly, and
  flaky-prone; keep them to the critical path.

## 4. Test through the public surface

- Never call `_private` functions or methods from a test. Reach the behavior
  via the public entry point (e.g. `main(args=[...])`, asserting exit code and
  stderr, instead of `_run_cmkpasswd(...)`).
- If a private function seems complex enough to need its own tests, move it
  into its own module with a public API. Direct tests of a complex internal
  algorithm are the rare exception, not the default.
- Assert on inputs, outputs, and visible side effects. Never on internal call
  sequences.
- When a test is hard to write, treat it as a structure problem: name it and
  fix or propose the structural change. Do not force the test through with
  patches and mocks.

## 5. Dependencies: decide how to supply, then what to supply

**How to supply a collaborator**

- Inject it as a parameter. This keeps dependencies explicit and avoids
  module-level globals.
- Patching (`unittest.mock.patch`, `mocker.patch`) couples the test to import
  paths: a move or rename breaks the test, or leaves it patching a name the
  code no longer uses.
- Patch only boundaries you do not own and cannot inject: stdlib I/O
  (`sys.stdin`), third-party HTTP (`requests.post`), OS calls, time,
  randomness, filesystem, network, and only when a fake is not worth building.
- All Checkmk code is owned code, whatever package it lives in. Patching your
  own internals, private functions, or Checkmk code from another
  package/component is a red flag.
- Legacy code that resists restructuring: patching is an accepted compromise.
  Treat it as technical debt, not as a pattern for new code.
- Even when patching, assert on observable outcomes, not on mock call details.

**What to supply**

Prefer a real instance when it is cheap. Otherwise:

| Double | Implementation                               | Use when                                                                                                                                                                 |
| ------ | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Stub   | `Mock(spec=X)` with `.return_value` set      | Collaborator is expensive or stateful to construct and the test only needs a canned answer. Assert on the outcome.                                                       |
| Fake   | Hand-written class with real in-memory state | Collaborator has meaningful state across calls (reads its own writes, accumulates history). Inject it; assert on the result and on the fake's state.                     |
| Mock   | `Mock()` + `assert_called_*`                 | Last resort: the call itself is the entire observable behavior, with no return value and no state to inspect (e.g. hook dispatch fires exactly the registered handlers). |

- Always pass `spec=` so stale attribute access fails immediately. No Protocol
  or interface is needed to stub a concrete class.
- `assert_called_*` pins implementation and is opaque to static analysis: a
  rename or rewiring breaks the test though behavior is unchanged. Reach for a
  stub or fake first. To check _what_ was sent, a fake that records calls (a
  list it appends to) is clearer than `assert_called_with`.

## 6. Seams: only where behavior really varies

- Justified seams: I/O boundaries, time, randomness, external services,
  anything whose behavior varies in production.
- Redundant seams: dependency injection for pure functions, interfaces around
  a collaborator that will only ever have one implementation, factories that
  exist only so a test can substitute a mock.
- Never add a seam whose only purpose is to let a test substitute something.

## 7. Shape of a single test

- **One behavior per test.** If you cannot name the behavior in a short
  sentence, split the test. Each test fails for exactly one reason.
- **Name the outcome, not the function.** `test_dangerous_markup_is_escaped`,
  `test_apply_matchers_stops_at_first_failure`. A bare function name such as
  `test_escape_to_html_permissive` is not a test name; the name must say what
  broke.
- **Arrange, Act, Assert** as three blocks separated by blank lines. No
  `# Arrange` / `# Act` / `# Assert` comments.
- **Assertions target observable outcomes.** Prefer one focused assertion;
  several are fine when they all describe the outcome of the same action.
  Failure output must say what broke.
- **Do not bundle operations.** "get returns None before any run" and "get
  returns the stored value after a store" are two tests.
- **Do not bundle rejections.** Several `pytest.raises` blocks in one function
  hide each other; parametrize.
- **Exception, state machines:** sequential act/assert cycles in one test are
  acceptable when each assert depends on the previous transition and splitting
  would duplicate setup or hide the dependency. Separate the cycles with blank
  lines.

## 8. Parametrize

- Use it when cases share one assertion and each case fits on one line. Give
  every case `pytest.param(..., id="descriptive name")` so the failing case is
  self-explaining.
- Keep the list short and focused. Wrap the decorator in `# fmt: off` /
  `# fmt: on` when a table layout helps scanning.
- An `if` on a parametrized argument inside the body means two behaviors are
  bundled. Split on the behavioral boundary
  (`test_allowed_tags_pass_through_unchanged` vs.
  `test_dangerous_markup_is_escaped`).
- When a case needs several lines, parametrize hurts readability; write
  separate named test functions.

## 9. Editions and non-free code

- Package and integration tests are edition-agnostic. A module's behavior does
  not change between editions, only whether it is deployed. No
  `skip_if_edition` / `skip_if_not_edition` markers: if the module exists, its
  tests run in every edition. Where the edition genuinely is an input to the
  logic, pass the edition enum as a plain test parameter.
- System tests test features, not editions: there are no "pro tests", there
  are "DCD tests". Every system suite runs parametrized by edition and declares
  the feature under test; the framework decides whether to run or skip.
- Artifact tests (`tests/packaging/`) are the one inherently edition-specific
  kind: they check that a build contains the expected files.
- Targets that depend on non-free libraries belong below `non-free/`. The
  legacy `tests/` tree still keeps them under `nonfree/` subdirectories
  instead, e.g. `tests/unit/cmk/gui/nonfree/`. Follow the placement of the
  neighboring tests.

## 10. Flaky tests

A flaky test passes and fails without a code change. Most flakes are in system
tests, for two reasons: a race between an action on the site (Livestatus, REST
API, UI) and checking its effect (files, settings, services), or a previous
test's teardown leaking into the next one (unactivated pending changes, a site
restart still in progress).

Writing site tests:

- After an action, wait for its effect with a timeout: the testlib's
  `wait_until_*` helpers for site state, Playwright's auto-waiting assertions
  for the UI. Never assert immediately after an asynchronous action.
- Teardown leaves no pending changes and does not restart the site into the
  next test.

When a test fails intermittently:

1. Do not skip, xfail, retry, or loosen an assertion to get a green run.
2. Reproduce first: run the test alone, repeatedly (`--count 10` with
   `--log-cli-level INFO`) and under CPU stress (`stress -c <cores minus 2>`).
   Check whether it fails for a valid reason before calling it flaky.
3. The component owner must confirm the flake. Informing them (Slack, in the
   existing thread or a public development channel) and creating the ticket
   are the developer's actions; prepare them, do not send them unasked.
   Tickets go to epic CMK-14217: type Incident for a flaky test
   implementation, Bug or Task for a defect in the source, assigned to the
   component owner; test-framework issues go to team QA, CI issues to team CI.
   The `/report-flaky-test` skill
   (`/plugins install report-flaky-test@checkmk-marketplace`) walks through
   investigate, find the owner, create the ticket, quarantine, retrigger.
4. Quarantine only after confirmation, referencing the ticket: Python
   `@pytest.mark.skip(reason="CMK-<ID>")`, Rust `#[ignore = "CMK-<ID>"]`, C++
   `GTEST_SKIP() << "CMK-<ID>";` or a `DISABLED_` test-name prefix. Then
   retrigger the pipeline.
5. The fix removes the skip in the same commit.

## 11. Frontend (Vue) tests

Tests for `packages/cmk-frontend-vue` live in its `tests/` directory, run on
vitest with `@testing-library/vue` (`bazel run :vitest -- <args>` from the
package, `bazel test :unit-test` for the whole suite). The same principle
applies as everywhere else: test along the public interface and assert
behavior, not implementation. The public interface of a UI component is the
props you pass in and the DOM it renders as seen through the accessibility
layer. For building blocks (`src/components/`, the UX-approved reusable
components) this style is enforced, and every behavior a building block
implements gets a test.

- Do: find elements through the accessibility layer,
  `screen.getByRole('<role>', { name: '<accessible name>' })`; drive them with
  `@testing-library/user-event`; simulate API backends with MockServiceWorker
  (grep `from 'msw'` for examples).
- Do not: drop down to `@vue/test-utils`; assert that events were emitted,
  mocks were called, CSS classes exist, or on values inside input fields.
- Do not reach into a child component's internals, in tests or in production
  code: no `document.querySelector()` or `v-deep` to change what a child
  renders. Variants are exposed through props.
- Visual regressions belong to screenshot tests, which do not exist yet.
- To see a change in the browser use the demo app, F12, or the hot-reload dev
  server; the package README lists the workflows. If a good test in this style
  seems impossible, that is a question for Team Bug, not a reason to test
  implementation details.

## 12. Self-check before finishing

- Test name is a function name with no stated outcome → rename to the outcome.
- Test calls a `_private` name → go through the public entry point, or promote
  the code to its own module.
- `patch(...)` targets Checkmk code in any package → inject the collaborator;
  in untouchable legacy code keep the patch and flag it as tech debt.
- `Mock()` without `spec=` → add `spec=`.
- `assert_called_*` present → if a return value or state exists, assert that
  instead; use a recording fake to check payloads.
- `if` on a parametrized argument → split into one test per behavior.
- Multi-line `pytest.param` rows → separate named tests.
- Several `pytest.raises` in one test → parametrize.
- `# Arrange` / `# Act` / `# Assert` comments → blank lines.
- New Protocol, factory, or constructor parameter in production code that only
  the test uses → remove it; stub or fake the concrete class, or test via the
  public surface.
- Same behavior asserted at two levels → delete the higher-level test.
- Unit test slower than ~10 ms or a suite over budget → fix the design or the
  level, not the timeout.
- Bug fix without a regression test → add one that fails without the fix.
- Doctest is the only coverage of some logic → add a real test.
- Test module not next to its source module's mirror path → move it.
- New suite in `tests/system/{singlesite,multisite,gui,gui_crawl,update,plugins}/`
  → move it to `tests/system/<feature>/`.
- `skip_if_edition` / `skip_if_not_edition` on a package or integration test →
  remove it; parametrize the edition if the logic needs it.
- Assertion right after a site action (REST call, activate changes, UI click)
  → wait for the effect with a timeout helper.
- Skip, xfail, retry, or loosened assertion added to get past an intermittent
  failure → revert it and follow the flaky-test process.
- Acceptance test expectation changed without stakeholder alignment → revert
  and raise it.
- Vue test imports `@vue/test-utils`, asserts emitted events, mock calls, CSS
  classes, or input values → rewrite with `@testing-library/vue` against roles
  and rendered text.
