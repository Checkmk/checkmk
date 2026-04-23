---
name: crash-report
description: Queries and reads crash reports from crash.checkmk.com
---

# Crash Report Skill

You are a specialized agent that queries and analyzes crash reports from crash.checkmk.com. The crash reporting service collects crash reports from Checkmk instances worldwide.

**CRITICAL: All crash report data contains customer-sensitive information (IP addresses, email addresses, hostnames). The helper script automatically anonymizes all data before output. NEVER attempt to de-anonymize or ask about original values.**

## Setup — Authentication

The skill authenticates with crash.checkmk.com using **Google OAuth** (preferred) or a legacy static token.

### Option 1: Google OAuth (recommended)

Run the authentication script — it opens a browser for Google Sign-In:

```bash
PYTHONPATH=.github/skills .venv/bin/python -m crash_report.authenticate
```

No setup required — the server handles the Google OAuth flow. This caches a temporary bearer token at `~/.cache/cmk-crash-reporting/token.json` (valid for 1 hour). The token is automatically used by all subsequent API calls. Re-run with `--force` to re-authenticate before expiry.

### Option 2: Legacy static token

Set the `CRASH_REPORTING_TOKEN` environment variable:

```bash
export CRASH_REPORTING_TOKEN='<token>'
```

The script checks for authentication in this order:

1. Cached OAuth bearer token (from `authenticate.py`)
2. `CRASH_REPORTING_TOKEN` env var (legacy)

If neither is available, the script will print instructions for how to authenticate.

## Arguments

The user provides a natural language request or a direct command. Examples:

- `/crash-report popular` — show popular unsolved crash groups
- `/crash-report search --unsolved --type check --min-crashes 5` — search with filters
- `/crash-report show <crash_id>` — show individual crash report
- `/crash-report group <group_id>` — show crash group details
- `/crash-report stats` — show aggregate statistics
- `/crash-report local` — list crash reports from local OMD sites
- `/crash-report auto-fix popular --limit 3` — auto-fix top 3 popular crash groups
- `/crash-report auto-fix search --type check --unsolved --limit 5` — auto-fix top 5 unsolved check crashes
- `/crash-report auto-fix --dry-run popular --limit 3` — analyze and fix but don't commit/push
- `/crash-report resolved --since 30d` — list crash groups fixed in the last 30 days
- `/crash-report resolve <group_id> --versions 2.4.0p8,2.3.0p25` — mark a crash group as resolved on the server (versions required)

## Workflow

### Step 1: Parse the Request

Translate the user's request into one of these commands:

| User intent                          | Command                                        |
| ------------------------------------ | ---------------------------------------------- |
| "Show me popular crashes"            | `popular`                                      |
| "What crashes happened last week?"   | `search --since 7d`                            |
| "Show check crashes with >5 reports" | `search --type check --min-crashes 5`          |
| "Unsolved GUI crashes for 2.4.0"     | `search --type gui --unsolved --version 2.4.0` |
| "Show crash report ABC-123-..."      | `show <crash_id>`                              |
| "Show crash group 42"                | `group 42`                                     |
| "Overall crash statistics"           | `stats`                                        |
| "Auto-fix popular crashes"           | `auto-fix popular --limit 5`                   |
| "Fix all unsolved check crashes"     | `auto-fix search --type check --unsolved`      |
| "What crashes are on my local site?" | `local`                                        |
| "Show local GUI crashes"             | `local --type gui`                             |
| "What crash groups did we fix?"      | `resolved --since 30d`                         |
| "Show resolved crashes this quarter" | `resolved --since 90d`                         |
| "Resolve group 42 in 2.4.0p8"        | `resolve 42 --versions 2.4.0p8`                |
| "Unresolve group 42"                 | `resolve 42 --unresolve`                       |

### Step 1.5: Check Authentication

Before running any query, check if a cached token exists and is valid:

```bash
PYTHONPATH=.github/skills .venv/bin/python -m crash_report check-auth
```

If the token is missing or expired (non-zero exit), run the authenticate command first:

```bash
PYTHONPATH=.github/skills .venv/bin/python -m crash_report.authenticate
```

This avoids failed API calls due to expired/missing credentials.

### Step 2: Run the Helper Script

```bash
PYTHONPATH=.github/skills .venv/bin/python -m crash_report <command> [options]
```

**Available commands:**

```bash
# Search crash groups with filters
PYTHONPATH=.github/skills .venv/bin/python -m crash_report search \
  [--since DATE] [--min-crashes N] [--type TYPE] [--unsolved] [--version VER] [--limit N]

# Popular unsolved crash groups (>10 crashes)
PYTHONPATH=.github/skills .venv/bin/python -m crash_report popular [--since DATE] [--limit N]

# Aggregate crash statistics
PYTHONPATH=.github/skills .venv/bin/python -m crash_report stats [--since DATE]

# Individual crash report (anonymized)
PYTHONPATH=.github/skills .venv/bin/python -m crash_report show <crash_id>

# Crash group detail (anonymized)
PYTHONPATH=.github/skills .venv/bin/python -m crash_report group <group_id>

# List crash reports from local OMD sites
PYTHONPATH=.github/skills .venv/bin/python -m crash_report local [--type TYPE]

# Mark a crash group as resolved (JWT auth required; legacy token rejected)
PYTHONPATH=.github/skills .venv/bin/python -m crash_report resolve <group_id> \
  --versions 2.4.0p8,2.3.0p25
PYTHONPATH=.github/skills .venv/bin/python -m crash_report resolve <group_id> --unresolve
```

The `resolve` command marks the group `is_solved=true` server-side, records the
authenticated user as `solved_by`, and stores the caller-supplied
`solved_versions` verbatim. `--versions` is required when resolving — the server
does not guess the fix versions. Use `--unresolve` to reverse a prior resolve
(no `--versions` needed).

Date arguments accept:

- ISO dates: `2025-01-15`
- Relative: `30d` (last 30 days), `7d` (last week)

### Step 3: Present Results

Present the output to the user in a readable format. The script outputs markdown tables and structured text.

### Step 4: Follow-up Actions

After presenting results, the next steps depend on what was shown:

**From a search/popular listing or statistics:**

- Offer to drill into a specific crash group or version.

**From a crash group:**

- Offer to show a specific crash report from the group.

**From an individual crash report (show):**

- **Automatically proceed to Step 5** (Explain the Issue) unless the user only asked for raw data.
- If a Jira issue is linked, mention it and offer to chain to `/jira-plan-ticket`.

---

### Step 5: Explain the Issue

After showing a crash report, automatically analyze it:

1. **Extract traceback locations.** Parse the `exc_traceback` for file paths and function names. Traceback paths are Checkmk source paths — they are NOT anonymized and can be used directly.

2. **Find the code in the local codebase.** Use Grep/Read to locate the crashing function. Since the crash report version may differ from the local `master` branch (line numbers shift), **search by function name and surrounding context**, not by exact line number. Example: if the traceback shows `File "cmk/gui/views.py", line 412, in render_view`, search for `def render_view` in `cmk/gui/views.py`.

3. **For check/section crash types:** The `details` field contains `host`, `service`, and `check_type`/`section_name`. Use these to locate the specific check plugin code (typically under `cmk/plugins/`). If `agent_output` is available (local crashes), show the relevant section.

4. **Present a summary:**
   - What function failed and why (correlate exception type/value with the code)
   - What input/state likely triggered it (from local_vars, details, agent_output)
   - Whether this looks like a bug in Checkmk code, a data/input issue, or an environmental problem

5. **Offer next steps:** Ask the user if they want to:
   - **Create a unit test** (Step 6)
   - **Fix the issue** (Step 7)
   - Both

---

### Step 6: Create Unit Test

Create a minimal `xfail` unit test that reproduces the crashing call from the traceback.

**Rules:**

1. **Test only the crashing call.** The test targets the specific function and call from the traceback that raised the exception — nothing more. Do not test the full workflow or surrounding logic.

2. **Mark as `@pytest.mark.xfail(strict=True)`.** The test documents the known bug. It should fail (proving the bug exists) and will be unmarked once the fix is applied. `strict=True` ensures CI fails if the test unexpectedly passes without a fix. Use `reason="Crash report <crash_id>: <ExcType>"` in the xfail marker.

3. **Reconstruct minimal inputs.** Use the crash report's `local_vars`, `details`, `agent_output`, and exception context to construct the minimal arguments that trigger the crash. Use anonymized/synthetic values — never embed real customer data.

4. **Place in the correct test directory.** Mirror the source path under `tests/unit/`. Example:
   - Source: `cmk/gui/views.py` → Test: `tests/unit/cmk/gui/test_views.py`
   - Source: `cmk/plugins/collection/agent_based/foo.py` → Test: `tests/unit/cmk/plugins/collection/agent_based/test_foo.py`

5. **Follow existing test conventions.** Before writing the test, read 1-2 existing test files in the same directory to match:
   - Import style and pytest fixtures (especially from `conftest.py`)
   - Naming conventions (`test_<function_name>_<scenario>`)
   - Any common test helpers or mocking patterns

6. **Run the test** using the `/bazel` skill to verify it fails as expected (xfail).

7. **Commit the test immediately** as the first commit. This commit contains **only** the xfail test file — no fix, no werk. Commit message: `Add xfail test for crash group <group_id>`

**Example test structure:**

```python
@pytest.mark.xfail(strict=True, reason="Crash report <id>: ValueError in parse_output")
def test_parse_output_crashes_on_empty_input() -> None:
    # Minimal reproduction from crash report local_vars/details
    result = parse_output("")  # triggers ValueError from traceback
```

---

### Step 6.5: Jira Ticket

Run **before the fix commit** in both the manual workflow (Step 7) and the auto-fix pipeline (between `(h) Werk` and `(j) Commit 2`). In auto-fix `--dry-run` mode: skip this step entirely.

**6.5.a. Lookup existing link.**
Re-use the `group <group_id>` output already fetched in Step 5. If the `Jira:` line is present and non-empty, record the key (e.g. `CMK-12345`) and jump to **6.5.f**. Otherwise continue with 6.5.b.

**6.5.b. Determine component.**
Collect the Checkmk-relative source paths from the crash traceback and ask the component owners tool:

```bash
cmk-components owners-for <path1> <path2> ...
```

Pick the most frequent component across the paths. If `cmk-components` is not installed or returns nothing, fall back to the compass-based match used by `jira-create-ticket` (run `.venv/bin/python .github/skills/jira-create-ticket/create_ticket.py --guess --summary "<drafted summary>"` and pick the closest match).

**6.5.c. Gather assignee + team.**
Auto-detect defaults:

- **Assignee** — the currently authenticated Jira user:

  ```bash
  .venv/bin/python -c 'import os; from jira import JIRA; \
      j=JIRA(server="https://jira.lan.tribe29.com", token_auth=os.environ["JIRA_API_TOKEN"]); \
      print(j.myself()["name"])'
  ```

- **Team** — the first team listed by compass for the component chosen in 6.5.b.

Always use `AskUserQuestion` to confirm / override both values — never commit these silently.

**6.5.d. Create the ticket.**
Chain to the existing helper:

```bash
.venv/bin/python .github/skills/jira-create-ticket/create_ticket.py \
  --summary "Fix crash in <component> (<exc_type>)" \
  --description "<Bug template: crash-group URL + anonymized traceback + observed/expected>" \
  --issue-type Bug \
  --component "<component>" \
  --developer-team "<team>"
```

Parse the `Created: CMK-XXXXX — <url>` line from stdout to capture the new key.

**6.5.e. Wire up assignee, story points, sprint, and "In Progress".**
Run a single inline python block (no file created) that uses the `jira` library to apply four updates. Wrap each call in its own try/except — one failure must not block the others. On failure, print `WARN: <field> update failed for <key>: <err>` and continue. Never abort the commit because of a Jira wire-up failure.

```bash
.venv/bin/python - <<'PY'
import os
from jira import JIRA

KEY = "<CMK-XXXXX>"
ASSIGNEE = "<assignee-username>"
TEAM = "<developer-team>"
STORY_POINTS_FIELD = "customfield_10106"

j = JIRA(server="https://jira.lan.tribe29.com", token_auth=os.environ["JIRA_API_TOKEN"])

try:
    j.assign_issue(KEY, ASSIGNEE)
except Exception as e:
    print(f"WARN: assignee update failed for {KEY}: {e}")

try:
    j.issue(KEY).update(fields={STORY_POINTS_FIELD: 2})
except Exception as e:
    print(f"WARN: story-points update failed for {KEY}: {e}")

try:
    boards = j.boards(name=TEAM)
    sprints = j.sprints(boards[0].id, state="active")
    j.add_issues_to_sprint(sprints[0].id, [KEY])
except Exception as e:
    print(f"WARN: sprint update failed for {KEY}: {e}")

try:
    tid = next(t["id"] for t in j.transitions(KEY) if t["name"] == "In Progress")
    j.transition_issue(KEY, tid)
except Exception as e:
    print(f"WARN: transition update failed for {KEY}: {e}")
PY
```

**6.5.f. Record the ticket for the commit trailer.**
Remember the Jira key — it will be added as a `Jira:` trailer on the fix commit (see Step 7 / auto-fix Commit 2).

---

### Step 7: Fix the Issue

After the explain step and the unit test commit, implement the fix:

1. **Minimal change only.** Fix the specific crash — do not refactor surrounding code, add unrelated error handling, or "improve" nearby logic.

2. **Remove the `@pytest.mark.xfail(strict=True, ...)` marker** from the test created in Step 6 so the test now asserts the correct behavior. Update the test assertion if the fix changes the expected output.

3. **Run tests and lint** using the `/bazel` skill to verify the fix passes.

4. **Create a werk** (changelog entry) by invoking the `/werk` skill — do not write to `.werks/` directly. The skill handles werk ID allocation, metadata validation, and the changelog commit.

5. **Run Step 6.5 (Jira Ticket)** to look up or create the tracking ticket before committing. Capture the resulting `CMK-XXXXX` key for the commit trailer.

6. **Create the second commit** containing the fix, the unmarked test, and the werk. This is the only content in this commit — the xfail test was already committed in Step 6. Use `Crash-Group-ID:` and `Jira:` trailers in the commit body:

   ```
   <werk_id>: Fix crash in <component> (<crash_type>)

   Crash-Group-ID: <group_id>
   Jira: CMK-XXXXX
   ```

---

### Auto-Fix Workflow

When the user invokes `auto-fix`, the agent runs a fully automated pipeline that processes crash groups end-to-end without interactive prompts. The syntax is:

```
auto-fix [--dry-run] [popular|search ...] [--limit N]
```

The arguments after `auto-fix` are passed directly to the `popular` or `search` command. If `--limit` is not specified, default to `--limit 5`.

**`--dry-run` mode:** When `--dry-run` is specified, the agent runs the full analysis pipeline (fetch, analyze, create test, fix, run tests) but stops before creating a werk, committing, or pushing. Each group's branch is left with uncommitted changes so the user can review. The summary table uses status "Dry run: fix ready" or "Dry run: fix failed" instead of "Pushed".

#### Pipeline

1. **Get crash groups.** Run the user's query (e.g. `popular --limit 3` or `search --type check --unsolved --limit 5`) to obtain the list of crash groups.

2. **For each crash group**, process sequentially:

   a. **Duplicate check.** Before starting work, check if this crash group has already been addressed:
   - Check for an existing local branch: `git branch --list '*crash-group-<group_id>'`
   - Check for an existing remote branch: `git branch -r --list '*crash-group-<group_id>'`
   - Check for an existing commit (branch name or trailer): `git log --all --oneline --grep='crash-group-<group_id>\|Crash-Group-ID: <group_id>'`

   If any match is found, skip this group with status "Skipped: existing branch/change found" and continue to the next group.

   b. **Branch.** Create a dedicated branch:

   ```bash
   git checkout master && git checkout -b sandbox/<username>/master/crash-group-<group_id>
   ```

   Where `<username>` is derived from `git config user.name` (lowercase, spaces replaced with hyphens).

   c. **Fetch details.** Run `group <group_id>` to get the group info. Pick the most recent crash ID from the group, then run `show <crash_id>` to get the full crash report.

   d. **Analyze.** Execute Step 5 (Explain the Issue) silently — do not prompt the user for next steps.

   e. **Unit test.** Execute Step 6 (Create Unit Test) — create an `xfail(strict=True)` test reproducing the crash.

   f. **Commit 1 (test only).** Stage and commit only the xfail test file:

   ```
   Add xfail test for crash group <group_id>
   ```

   g. **Fix.** Execute Step 7 (Fix the Issue) — implement the fix, remove `xfail(strict=True)`, run tests and lint via `/bazel`.

   h. **Werk.** Invoke the `/werk` skill to create the werk with class `fix`, level `1`, and the appropriate component inferred from the crash type and file path. Do not write to `.werks/` or edit `.werks/first_free` directly — the `/werk` skill manages werk IDs and metadata.

   i. **Jira ticket.** Execute Step 6.5 (Jira Ticket) to look up or create the tracking ticket. Capture the resulting `CMK-XXXXX` key for the commit trailer. Skip this sub-step entirely when `--dry-run` is active.

   j. **Confidence check.** Before committing, self-assess the fix confidence as **high**, **medium**, or **low**:
   - **High:** The crash has a clear root cause, the fix is a small localized change, and all tests pass.
   - **Medium:** The fix is reasonable but touches non-trivial logic, or the crash context is ambiguous.
   - **Low:** The fix is speculative, involves multiple files, or the agent is unsure about side effects.

   k. **Commit 2 (fix + unmarked test + werk).** Stage the fix, the unmarked test, and the werk, then commit with `Crash-Group-ID:` and `Jira:` trailers:

   ```
   <werk_id>: Fix crash in <component> (<crash_type>)

   Crash-Group-ID: <group_id>
   Jira: CMK-XXXXX
   ```

   l. **Push (high confidence only).** If confidence is **high**, push to Gerrit:

   ```bash
   git push -u origin <branch>
   ```

   If confidence is **medium** or **low**, do NOT push. The branch is committed locally. The summary table reports these as "Local only (medium confidence)" or "Local only (low confidence)" so the user can review before pushing.

   m. **Return.** Switch back to master for the next group:

   ```bash
   git checkout master
   ```

   **Do NOT mark the group as resolved on the server** as part of this pipeline. Server-side resolve is a separate, explicitly-permitted step (see "Mark Resolved on Server" below) that the user opts into after verifying the fix has actually been merged and released.

3. **Summary.** After all groups are processed, print a summary table:

   | Group ID | Crash Type | Branch                     | Confidence | Status                          |
   | -------- | ---------- | -------------------------- | ---------- | ------------------------------- |
   | 42       | check      | sandbox/.../crash-group-42 | High       | Pushed                          |
   | 57       | gui        | sandbox/.../crash-group-57 | Medium     | Local only (medium)             |
   | 63       | check      | sandbox/.../crash-group-63 | —          | Skipped: already solved         |
   | 71       | gui        | sandbox/.../crash-group-71 | —          | Failed: tests fail, branch kept |
   | 85       | check      | —                          | —          | Skipped: existing branch found  |

#### Skip / Failure Handling

The agent should **skip** a crash group (and report it in the summary) if:

- **Duplicate:** A local or remote branch matching `*crash-group-<group_id>` already exists, or a commit message references it.
- **Already solved:** The group data has `solved: true`.
- **Code not found locally:** The traceback points to source files or functions that don't exist in the local `master` branch (version mismatch too large).
- **Too complex:** The fix would require non-trivial architectural changes that the agent cannot confidently implement.
- **Tests fail after fix:** If tests still fail after the fix attempt, commit the work-in-progress on the branch (with message `WIP: crash-group-<group_id> — tests failing`), switch back to master, and report the group as "Failed: tests fail, branch kept". Do NOT delete the branch — the user may want to inspect or continue the partial fix.

When a group is skipped, log the reason and continue to the next group. Do not prompt the user.

---

### Resolved Crash Groups

The `resolved` command lists crash groups that have been fixed by searching git history for `Crash-Group-ID:` trailers in commit messages.

**Syntax:**

```
resolved [--since DATE] [--branch BRANCH]
```

- `--since`: How far back to search (default: `90d`). Accepts ISO dates or relative dates like `30d`.
- `--branch`: Git branch to search (default: current branch). Use `--branch --all` to search all branches.

**This is an agent-executed workflow, not a helper script subcommand.** The agent performs these steps:

1. **Search git log** for commits containing the `Crash-Group-ID:` trailer:

   ```bash
   git log [<branch>] --grep='Crash-Group-ID:' --format='%H' [--since=<date>]
   ```

2. **Extract group IDs** from each matching commit by reading the trailer:

   ```bash
   git log --format='%(trailers:key=Crash-Group-ID,valueonly)' -1 <commit_hash>
   ```

3. **Get Gerrit change link** for each commit. Extract the `Change-Id` trailer and look up the change number:

   ```bash
   git log --format='%(trailers:key=Change-Id,valueonly)' -1 <commit_hash>
   ```

   Construct the Gerrit URL: `https://review.lan.tribe29.com/c/check_mk/+/<change_number>`

   If the Gerrit lookup fails, fall back to the short commit hash.

4. **Fetch crash group details** for each unique group ID using the helper script:

   ```bash
   PYTHONPATH=.github/skills .venv/bin/python -m crash_report group <group_id>
   ```

   Extract the crash group URL, crash type, and solved versions from the output.

5. **Present a summary table:**

   | Group ID | Type  | Crash Group                           | Gerrit                                                            | Solved Versions   |
   | -------- | ----- | ------------------------------------- | ----------------------------------------------------------------- | ----------------- |
   | 42       | check | [Link](https://crash.checkmk.com/...) | [Change 12345](https://review.lan.tribe29.com/c/check_mk/+/12345) | 2.4.0p7, 2.3.0p25 |
   | 57       | gui   | [Link](https://crash.checkmk.com/...) | [Change 12400](https://review.lan.tribe29.com/c/check_mk/+/12400) | 2.4.0p7           |

**Note:** This command only finds crash groups fixed using the `Crash-Group-ID:` commit trailer convention. Older fixes without this trailer will not appear.

**Follow-up:** After presenting the table, offer to run "Mark Resolved on Server" (below) for any row where the user confirms the fix is merged and released.

---

### Mark Resolved on Server

After a crash group has been fixed **and the fix has actually been merged and released**, the user may ask to mark the group as resolved on crash.checkmk.com so it stops showing up in unsolved-crash queries and customers get notified.

**This step is never automatic.** Do not run it as part of `auto-fix`, and do not run it silently after `resolved`. Always get explicit user confirmation (via `AskUserQuestion`) for each group before calling the endpoint.

**Command:**

```bash
PYTHONPATH=.github/skills .venv/bin/python -m crash_report resolve <group_id> \
  [--versions 2.4.0p8,2.3.0p25] [--unresolve]
```

- `--versions`: **required when resolving.** Comma-separated list of Checkmk versions that contain the fix (e.g. `2.4.0p8,2.3.0p25`). The server does not guess — pass the specific patch releases the fix landed in. Check the werk and any backport commits to determine these.
- `--unresolve`: reverse a prior resolve (e.g. after discovering the fix was incomplete). `--versions` is not needed with `--unresolve`.

**Authentication:** requires JWT auth (run `authenticate.py` if needed). The legacy static token is rejected server-side because the endpoint records the authenticated user as `solved_by`.

**Typical flow:**

1. User runs `resolved --since 30d` (or hands over a list of group IDs they want to close out).
2. For each group, ask: "Mark group `<id>` as resolved on the server? (versions: `<auto|explicit>`)".
3. On `yes`, run the `resolve` command. On `no` or skip, move on.
4. Report the server's response (solved_by, solved_at, solved_versions).

---

## New File License Headers

When any step creates a new file (test file, helper, etc.), use the **current year** (run `date +%Y` if unsure) in the Checkmk license header:

```python
# Copyright (C) <CURRENT_YEAR> Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
```

## Local OMD Site Fallback

The `show` command automatically falls back to local OMD sites when the crash report is not found on crash.checkmk.com (or the remote API is unreachable). It scans `/omd/sites/*/var/check_mk/crashes/<type>/<crash_id>/crash.info`.

The `local` command lists all crash reports found in local OMD sites without contacting the remote API. This is useful for:

- Viewing crashes that haven't been uploaded yet
- Working offline or without API access
- Debugging crashes on a development site

Note: Accessing local OMD site crash reports may require running as the site user or with appropriate file permissions.

## Important Notes

- All crash data is **automatically anonymized** by the helper script. You will see anonymized IPs (10.0.x.x, 203.0.x.x), emails (user1@example.com), and hostnames (host1.example.com).
- **Traceback file paths are NOT anonymized** — these are Checkmk source code paths needed for debugging.
- The `stats` command returns only aggregate counts and needs no anonymization.
- The API requires the crash reporting service to have the new `/search`, `/crash_report/<id>`, and `/crash_group/<id>` endpoints deployed. If you get 404 errors on these endpoints, fall back to the `popular` and `stats` commands which use the older API.
