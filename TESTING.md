# Testing rules

The testing guidelines live in the developer documentation. Before you write,
change or debug tests, read
[doc/documentation/dev-testing.rst](doc/documentation/dev-testing.rst) and the
guides below that apply to your change.

| Guide                                                                   | Read when you                                                       |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------- |
| [Test classification](doc/documentation/dev-testing-classification.rst) | add a test file, pick a directory, run tests, or deal with editions |
| [Flaky tests](doc/documentation/dev-testing-flaky.rst)                  | write a site test or investigate an intermittent failure            |
| [Python / pytest](doc/documentation/dev-testing-python.rst)             | write or change a Python test                                       |
| [Vue / vitest](doc/documentation/dev-testing-vue.rst)                   | write or change a test in `packages/cmk-frontend-vue`               |

The core rules: test behavior through the public surface, inject dependencies
instead of patching Checkmk code, and cover one behavior per test.

## Self-check before finishing

**Every test**

- The test name states the behavior, not the function under test.
- The test uses only the public surface; it calls no private functions.
- No Checkmk code is patched; collaborators are injected.
- No check on how a mock was called where a result or state could be
  checked instead.
- No Protocol, factory or constructor parameter in new production code that
  only the test uses. Legacy code may need such seams to get under test
  before it is restructured.
- Each test covers one behavior, and no behavior is tested at two levels.
- Arrange, Act and Assert are separated by blank lines, not comments.
- Every bug fix has a regression test that fails without the fix.

**Placement and editions**

- The test module mirrors its source module's path.
- No new suite in
  `tests/system/{singlesite,multisite,gui,gui_crawl,update,plugins}/`.
- No package or integration test is skipped by edition.
- No doctest is the only coverage of some logic.

**Site tests and flakes**

- No assertion right after a site action (REST call, activate changes, UI
  click) without waiting for the effect.
- No skip, xfail, retry or loosened assertion added to get past an
  intermittent failure without a confirmed ticket.

**Python**

- Every `Mock()` has `spec=`.
- No `if` on a parametrized argument; split into one test per behavior.
- No test with several `pytest.raises` blocks; parametrize.
- No bare `assert` in `tests/testlib`; raise `AssertionError` or
  `RuntimeError` with a message.

**Vue**

- No `@vue/test-utils`, and no assertions on emitted events, mock calls, CSS
  classes or input values; use `@testing-library/vue` against roles and
  rendered text.
