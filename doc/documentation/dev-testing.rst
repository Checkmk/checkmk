==================
Testing guidelines
==================

Based on the internal wiki page "Guideline: Testing". Where this page and the
wiki disagree, the wiki wins. The pages linked at the end hold the details.

Our test suite is a safety net. It should catch regressions without slowing
development down. A good test is:

* **Expressive.** A reader sees at once what the test protects.
* **Clearly bounded.** If a test is hard to write, the module usually needs a
  better structure.
* **Fast and reliable.** No flakes, no ten-minute suites.
* **Failing for useful reasons.** Red means the behavior is broken, not that
  someone renamed a private method.

**Behavior** is what a caller observes through the public interface: function
signatures, REST endpoints, CLI commands, exported libraries.

**Default rule:** test behavior at the component boundary, through the public
interface. Use unit and component tests for internal logic. Use system tests
only for critical user paths that span several components.

Why we test
===========

Untested code is broken; we just do not know it yet. Tests prevent
regressions, make refactoring safe and give fast feedback. They are also the
first users of an API, so they expose bad coupling early. Ask "how will we
know this works?" before you write the first line, and if a bug can happen
twice, let a test catch it the first time.

Automated tests only catch what you expected to go wrong. Before you call a
change done, run the real workflow once yourself.

What to test
============

Every test is code that someone must maintain. More tests are not
automatically better.

* **Write a test for** user-visible flows and contracts, branching logic,
  error and failure paths, module boundaries where a change on one side can
  silently break the other, and areas with a history of regressions. Every
  bug fix needs a regression test that fails without the fix.
* **Do not write a test for** trivial code, the internals of third-party
  libraries, behavior that another test already covers, or excessive
  parameter variations.

Picking the level
=================

Pick the level by behavior, not by habit. Describe the behavior in one
sentence a non-engineer could understand, then pick the level that verifies it
honestly and cheaply: low enough to pinpoint a failure, high enough to survive
a restructure.

* For most code, the behavior lives at the public interface of one component,
  and the test belongs there. If that interface is a library API, test the
  API. If it is a web server or CLI, test the running process through its REST
  endpoints or command line.
* Tests of internal classes usually give less confidence than tests of the
  component's public surface.
* Verify each behavior once. If two tests at different levels cover the same
  behavior, delete the higher-level one.
* Keep system tests to the most critical workflows. They are slow, expensive
  to maintain and prone to flakes.

:doc:`dev-testing-classification` defines the levels and says where each kind
of test lives.

Runtime targets
===============

=================  ============================
Scope              Target
=================  ============================
One unit test      1–10 ms
Component suite    < 10 min
Integration suite  < 10 min
System suite       < 30 min, critical path only
=================  ============================

A test over its budget signals a design problem. Fix the design or the level;
do not raise the budget.

Testing through the public surface
==================================

* **Assert on inputs, outputs and visible side effects**, never on internal
  call sequences. A good test breaks when the outcome is wrong, not when the
  implementation changes.
* **Do not call private functions or methods from a test.** Reach the
  behavior through the public entry point.
* **If a private function needs its own tests, move it** into a module with a
  public API. Tests of a complex internal algorithm are the rare exception.

Dependencies: doubles, injection and patching
=============================================

First decide how to supply a collaborator, then what to supply.

**How:** inject the collaborator as a parameter. Injection makes the
dependency explicit and improves the structure. Avoid patching: it couples the
test to import paths, so moving or renaming code breaks the test.

* **Patching is acceptable** for third-party code and for real external
  boundaries (time, randomness, filesystem, network) where a fake is not worth
  building. Checkmk code in any package is not third-party code.
* **Patching is a red flag** when it targets your own internals, private
  functions or Checkmk code from another package.
* **In legacy code** that resists restructuring, patching is an accepted
  compromise. Treat it as technical debt, not as a pattern for new code.

**What:** use a real instance when it is cheap. Otherwise pick a double. Most
of what engineers call "a mock" is really a stub.

* **Stub:** returns canned answers.
* **Fake:** a lightweight working implementation, such as an in-memory
  database or a deterministic clock.
* **Mock:** a stub that also verifies how it was called. Avoid mocks: they pin
  the implementation instead of the behavior, and static analysis cannot see
  through them. Use one only when the call itself is the whole observable
  behavior.

Designing for testability
=========================

If new code is hard to test, fix its structure, but do not give up readability
for testability. Name the structural problem and fix it or propose a fix; do
not force the test through with patches and mocks.

In new code, a seam is justified only where behavior varies in production or
at a real external boundary.

* **Useful seams:** I/O boundaries, time, randomness, external services.
* **Redundant seams:** dependency injection for pure functions, interfaces
  around a collaborator with only one implementation, factories that exist
  only so a test can swap in a mock.

Legacy code without tests reverses the order: get it under test first, by
whatever means it takes, then restructure it. Patches, mocks and seams that
only the test uses are acceptable here. They are the safety net for the
refactoring, and you remove them as the structure improves.

Shape of a single test
======================

* **One behavior per test.** If you cannot name the behavior in a short
  sentence, split the test.
* **Arrange, Act, Assert** form three visibly separate blocks, without
  comments to label them.
* **Name the behavior.** "discount is applied for gold members", not
  "calculate_price returns 150". The name should say what broke.
* **Assert on observable outcomes:** API responses, UI changes, visible side
  effects. One focused assertion beats several vague ones, and the failure
  message must say what broke.

Further guides
==============

* :doc:`dev-testing-classification`: test levels, where tests live, how to run
  them, editions and non-free code.
* :doc:`dev-testing-flaky`: writing site tests and handling intermittent
  failures.
* :doc:`dev-testing-python`: applying these rules with pytest.
* :doc:`dev-testing-vue`: applying these rules to Vue components.
