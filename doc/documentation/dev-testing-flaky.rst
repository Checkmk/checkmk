===========
Flaky tests
===========

This page describes how to avoid flaky tests and how to handle one. It is
based on the internal wiki page "Guideline: Flaky Tests". Read the
:doc:`dev-testing` first.

A flaky test passes and fails without a change to the code under test. Most
flakes occur in system tests, for two reasons:

* **Timing:** the test acts on the site (via Livestatus, REST API or UI) and
  checks the effect (files, settings, services) before the site has applied
  it.
* **Faulty teardown:** an earlier test leaks state into the next one, such as
  unactivated pending changes or a site restart still in progress.

Writing site tests
==================

* After an action, wait for its effect with a timeout. Use the testlib's
  ``wait_until_*`` helpers for site state and Playwright's auto-waiting
  assertions for the UI. Never assert immediately after an asynchronous
  action.
* Make teardown leave no pending changes and no site restart for the next
  test.

Handling an intermittent failure
================================

1. Do not skip, xfail, retry or loosen an assertion to get a green run.
2. Reproduce first. Run the test alone and repeatedly, also under CPU load
   (``stress -c <cores minus 2>``). Check whether it fails for a valid reason
   before you call it flaky.
3. Inform the component owner, who must confirm the flake. Post in the Slack
   thread that already discusses the failure, or in a public development
   channel, so others who hit it see that it is reported. The owner then
   creates a ticket under epic CMK-14217:

   * type Incident for a flaw in the test,
   * type Bug or Task for a defect in the source, assigned to the component
     owner,
   * test-framework issues go to team QA, CI issues to team CI.

   Messages and tickets go out under the developer's name. Draft them; do not
   send them unasked.
4. Quarantine the test only after the owner confirms the flake, and reference
   the ticket in the skip reason:

   * Python: ``@pytest.mark.skip(reason="CMK-<ID>")``
   * Rust: ``#[ignore = "CMK-<ID>"]``
   * C++: ``GTEST_SKIP() << "CMK-<ID>";`` or a ``DISABLED_`` prefix on the
     test name

   Then retrigger the pipeline.
5. The commit that fixes the test also removes the skip.

The ``/report-flaky-test`` skill
(``/plugins install report-flaky-test@checkmk-marketplace``) walks through
this process: investigate, find the owner, create the ticket, quarantine,
retrigger.
