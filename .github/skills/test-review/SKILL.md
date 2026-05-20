---
name: test-review
description: Use when reviewing tests or test changes in a diff, pull request, or merge request. Triggers on assessing test quality, spotting test anti-patterns, or evaluating whether an assertion earns its place.
---

# Test Review

A checklist for reviewing tests. Use it to surface anti-patterns and red flags
in test code, and to judge whether a test sits at the right level.

## Anti-patterns

- **Brittle mocking.** Mocks that verify unimportant call sequences cause tests
  to break during refactoring. Assert on outcomes instead.
- **Patching internals.** Reaching into private code couples tests to
  implementation details. Inject dependencies or move the test to a higher
  level. Only acceptable for legacy code, even then prefer to refactor and remove the mock/patch.
- **Always-passing tests.** Ensure assertions can fail by temporarily breaking
  the production code. Automated tests only catch expected errors; manual
  verification is still necessary.
- **Vague failure messages.** If a failure doesn't clearly explain the problem,
  improve the assertion or split the test.
- **Fixture soup.** Shared setup that no single test fully needs, so every
  change to a fixture breaks something unrelated. Auto-enabled fixtures also
  make it harder to understand test setup and failures. Prefer a small, local
  setup to a pyramid of fixtures.
- **Non-local fixtures.** Keep fixtures near the test code. Reserve shared
  fixtures for the rare cases where many tests require identical setup. If a
  fixture must be non-local, choose a name that reveals its scope and limit its
  use to truly universal setup. Default to local fixtures.
- **Clever test code.** Boring test code is good test code; if a junior
  engineer can't follow it, it's too complex. Tests aren't in the main binary,
  but they are in the maintenance budget. Helpers with six arguments, custom
  DSLs for one file, and inheritance hierarchies of test classes are
  liabilities.
- **Redundant high-level assertions.** Re-asserting at component or E2E level
  what lower tests already cover slows the suite and obscures what the
  higher-level test is actually protecting.
- **Mocked-out "user flow" tests.** A test that claims to exercise a flow but
  stubs the interesting parts of it. At that point it is a unit test in
  disguise, and a brittle one.
- **Unit test wearing a flow's clothes.** A unit test whose name and
  assertions describe a user-visible flow. Promote it or replace it with the
  component test it is standing in for.
- **Flaky tests.** Intermittent failures destroy trust in the CI pipeline. Fix
  or remove unstable tests immediately.
- **Test does multiple things.** If you can't name in one sentence what
  behavior the test protects, it's doing too much. Failures from omnibus tests
  are slower to diagnose and easier to misread. Split it.
- **No visible AAA shape.** Arrange, act, and assert should be readable at a
  glance, without explicit comments. Setup, action, and assertion interleaved
  through the test body make failures harder to localize.
- **Test-induced over-engineering.** Dependency injection on pure functions,
  interfaces around trivial collaborators that will only ever have one
  implementation, factories whose only consumer is a test. Production seams
  must be justified by production behavior, not by test convenience.

## Red flags — quick scan

The short checklist version. This is what to link to in an MR:

- Does this test fail for a reason someone can act on?
- Is anything being patched that we own?
- Does the test name describe a behavior, or a mechanism?
- Is this the right level, or is it mocking its way around being one?
- Is this unit test actually describing a user flow? Should it be promoted or
  replaced by a component test?
- Does static analysis already guarantee what this test is checking?
- Is this test being reviewed as carefully as the production code next to it?
  Tests don't test themselves.
- Do the assertions just restate the implementation? If so, the test isn't
  earning its place.

## Symptoms you're at the wrong level

- A unit test that just restates what the type checker already enforces →
  delete it.
- A unit test that needs extensive mocking of a package's own internals → the
  behavior probably lives at the component level; let the real collaborators
  run.
- A system test asserting behavior at a lower level could catch → move the
  assertion down.
- Positive counterpart: a system test earns its place when it would catch a
  regression that no lower level could.
