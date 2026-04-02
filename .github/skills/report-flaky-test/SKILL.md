---
name: report-flaky-test
description: Investigate a flaky test, identify the component owner, create a Jira ticket, and quarantine the test
---

# Flaky Test

Guides the developer through the flaky test process: investigate the failure, identify the component owner, create a tracking ticket, quarantine the test, and retrigger the pipeline.

## Arguments

The user provides one of:

- A **Jenkins URL** showing a build with a failing test
- A **test name or file path** of a suspected flaky test
- A **Jira ticket key** for an already-confirmed flaky test (skips to quarantine)

Examples:

- `/flaky-test https://ci.lan.tribe29.com/job/.../123`
- `/flaky-test tests/unit/cmk/gui/test_views.py::test_render`
- `/flaky-test CMK-12345` (skip investigation, quarantine only)

## Workflow

### 1. Parse the input

Determine what the user provided:

- **Jenkins URL** → proceed to Step 2 (investigate CI failure)
- **Test name or path** → proceed to Step 3 (locate the test)
- **Jira ticket key** (matches `CMK-\d+`) → skip to Step 7 (quarantine). Fetch the ticket summary using the jira-read-ticket helper to confirm it's a flaky test ticket:

  ```bash
  .venv/bin/python .github/skills/jira-read-ticket/read_ticket.py <TICKET_KEY>
  ```

### 2. Investigate the CI failure

Use `jenkins_build_data.py` to fetch the build details:

```bash
jenkins_build_data.py <URL> --include=stages,tests --failed-only
```

From the output, identify:

- The **failing test name(s)** and their error messages
- Whether the failure looks like a flake (non-deterministic error, timeout, race condition, ordering dependency) vs. a legitimate regression

If the failure points to a triggered sub-job, drill in:

```bash
jenkins_build_data.py <triggered-job-url> --include=console,tests
```

Present the findings to the user:

- Test name and file path
- Error message / traceback summary
- Whether this looks like a flake or a real failure (with reasoning)

If the failure does NOT look like a flake (clear code bug, missing import, syntax error, etc.), tell the user and suggest fixing the test instead. Do not proceed with quarantine for non-flaky failures.

### 3. Locate the test in the codebase

Search for the test function in the local codebase:

```bash
grep -r "def <test_function_name>" tests/
```

If the test is found, read the test file to understand:

- What the test does
- What code it exercises (the **code under test**)
- Any markers, fixtures, or parametrization that might be relevant

If the test is NOT found locally (e.g. it was recently added or removed), inform the user and ask how to proceed.

### 4. Identify the component owner

Determine who owns the **code under test** (not the test file itself). Use the imports and calls in the test to identify the production code path, then query the component owner:

```bash
cmk-components owners-for <path-to-code-under-test>
```

Also get the component name:

```bash
cmk-components component-for <path-to-code-under-test>
```

If `cmk-components` is not available, fall back to checking the directory structure and any `OWNERS` files near the code under test.

### 5. Present findings and guide user to contact the component owner

Present a summary to the user:

- **Flaky test**: name and file path
- **Error**: brief description of the failure
- **Code under test**: the production code path(s) exercised by the test
- **Component**: the component name
- **Component owner**: team or person responsible

Then instruct the user:

> **Next step:** Contact the component owner to confirm this is a flake.
> Best practice is to ping them via Slack — either in an existing thread about this failure or in a public development channel so others know it's reported.
>
> Once the component owner confirms the flake, tell me and we'll proceed to create a ticket and quarantine the test.

Wait for the user to confirm before proceeding.

### 6. Create a Jira ticket

Once the flake is confirmed, create a Jira ticket using the `/jira-create-ticket` skill. Pre-fill the following:

- **Issue type**: Bug
- **Summary**: `Flaky test: <test_name>`
- **Description** (use Bug template from jira-create-ticket):

  ```
  {panel:title=Acceptance Criteria|titleBGColor=#15d1a0}
   * The test passes reliably without flakiness
   * The skip marker is removed in the same commit as the fix{panel}
  h3. Steps to reproduce

   # Run the test repeatedly or observe CI failures

  h3. Observed behavior

  The test <test_name> fails intermittently in CI without code changes.

  Error: <error summary>

  h3. Expected behavior

  The test should pass reliably on every run.

  h3. Root cause

  Currently the root cause is unknown.

  h3. Additional resource / Screenshots

  <Jenkins URL if available>

  See attachments for CI failure logs and screenshots.
  ```

- **Component**: as determined in Step 4

Invoke the `/jira-create-ticket` skill with this pre-filled information. The skill will handle component/team guessing, user confirmation, and ticket creation.
Link the ticket to the Flaky Tests epic CMK-14217.

**Important:** The component owner is responsible for aligning prioritization with the product owner. The fix should be scheduled as soon as possible.

### 7. Preserve CI evidence

If the flaky test was discovered from a Jenkins build URL, collect the relevant evidence and attach it to the Jira ticket so the information survives Jenkins log rotation. Most developers do not have permissions to mark builds as "keep forever", so we preserve evidence by attaching it directly.

Collect the following from the Jenkins build:

1. **Test failure output**: the error message and traceback from the failing test (already gathered in Step 2)
2. **Console log excerpt**: the relevant portion of the console log around the failure
3. **Screenshots or artifacts**: if the build produced screenshots (e.g. GUI E2E tests) or crash reports, download them

Use `jenkins_build_data.py` to fetch console output if not already retrieved:

```bash
jenkins_build_data.py <URL> --include=console,tests
```

Save the collected evidence (error logs, console excerpts, screenshots) to temporary files, then attach them to the Jira ticket using `attach_evidence.py`:

```bash
.venv/bin/python .github/skills/report-flaky-test/attach_evidence.py <TICKET_KEY> /path/to/ci-failure-log.txt [/path/to/screenshot.png ...]
```

Also add the Jenkins build URL to the ticket description so reviewers can access it while the build logs still exist.

### 8. Quarantine the test

After the ticket is created (or if a ticket key was provided directly in Step 1), add the appropriate skip marker to the test.

Determine the test language and framework:

#### Python (pytest)

Add `@pytest.mark.skip(reason="<TICKET_KEY>")` as a decorator just before the test function:

```python
@pytest.mark.skip(reason="CMK-12345")
def test_example() -> None:
    ...
```

If the test is parametrized, place the skip marker **before** `@pytest.mark.parametrize` so it skips all parameter combinations:

```python
@pytest.mark.skip(reason="CMK-12345")
@pytest.mark.parametrize("param", [...])
def test_example(param) -> None:
    ...
```

If only specific parameter combinations are flaky, prefer `skipif` or conditional `xfail` — but in general, skip the whole test to be safe.

#### Rust

Add `#[ignore = "CMK-12345"]` just before the test function:

```rust
#[ignore = "CMK-12345"]
#[test]
fn test_example() {
    ...
}
```

#### C++ (Google Test)

Add `GTEST_SKIP() << "CMK-12345";` as the first line of the test body:

```cpp
TEST(TestSuite, TestName) {
    GTEST_SKIP() << "CMK-12345";
    ...
}
```

Or prefix the test name with `DISABLED_`:

```cpp
TEST(TestSuite, DISABLED_TestName) {
    ...
}
```

Prefer the `GTEST_SKIP()` approach as it preserves the original test name and includes the ticket reference.

### 9. Run linters and formatters

Format and lint the modified test file:

```bash
bazel run //:format <test-file-path>
```

Then run `bazel lint --fix` to auto-fix any lint issues.

### 10. Commit the quarantine

Commit the change with a clear message referencing the ticket:

```
Skip flaky test <test_name> (<TICKET_KEY>)
```

The commit should contain ONLY the skip marker change — no other modifications.

### 11. Draft a Slack message for the component owner

After committing, draft a ready-to-send Slack message for the user to send to the component lead. Include:

- The flaky test name and file path
- Brief description of the failure
- Link to the Jira ticket
- Link to the Jenkins build (if available)
- Note that the test has been quarantined and the skip marker should be removed in the same commit as the fix

### 12. Guide the user to retrigger the pipeline

After committing, tell the user:

> **Done.** The test has been quarantined with a reference to <TICKET_KEY>.
>
> **Next steps:**
>
> 1. Push this change and retrigger the CI pipeline to verify it passes without the flaky test.
> 2. The component owner is responsible for fixing the flaky test and removing the skip marker in the same commit as the fix.
> 3. The fix should be prioritized with the product owner — ideally in the current sprint if capacity allows, or in one of the next sprints.

## Notes

- The skip marker must be removed in the **same commit** as the fix — never separately.
- If the user discovers multiple flaky tests at once, process them one at a time. Each flaky test gets its own ticket.
- If the component owner disputes that the test is flaky, do NOT quarantine it. Work with the owner to understand the real cause.
- For technical difficulties with the fix (e.g. freezegun issues, complex restructuring), the component owner should escalate to the tech lead.
- For decisions requiring major design changes, escalate to the development lead.
