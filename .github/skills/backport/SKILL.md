---
name: backport
description: Backport a commit or branch to a stable release branch (e.g. "backport this to 2.5", "backport to 2.4.0"). Creates a new branch off the target stable branch, cherry-picks the commit(s), resolves path conflicts that arise from structural differences between master and stable branches, then runs formatter, linter, and tests.
---

# Backport Workflow

Backports a change from the current (master) branch to a stable release branch.

## Arguments

The user provides a target version (e.g. `2.5`, `2.4.0`). Normalize it to the full branch name used in the repo (e.g. `2.5` → `2.5.0`, `2.4` → `2.4.0`).

The commit(s) to backport are the top commit(s) on the current branch unless the user specifies otherwise. Identify the commit hash(es) with `git log`.

## Workflow

### 1. Create a task list

Before doing anything, create tasks to track progress:

- Create backport branch off `origin/<TARGET>`
- Cherry-pick commit(s) via `werk cherry-pick`
- Resolve conflicts if any
- Run formatter, linter, and tests

Mark each task in_progress when starting it and completed when done.

### 2. Determine the branch name

The backport branch name is the current branch name with `-<TARGET>` appended.

Example: `CMK-32502/warn-on-no-user-namespaces` → `CMK-32502/warn-on-no-user-namespaces-2.5`

### 3. Create the backport branch

```bash
git checkout -b <BACKPORT_BRANCH> origin/<TARGET_BRANCH>
```

### 4. Cherry-pick

Always use `werk cherry-pick` instead of plain `git cherry-pick`. It handles the cherry-pick **and** automatically updates the `version` field in any werk files to the correct version for the target branch.

The `werk` tool must come from **the backport branch's venv**, not master's venv, to ensure the werk version is correct for the target branch. Install the venv on the backport branch first:

```bash
# Build the venv on the backport branch
make .venv

# Run werk cherry-pick using the backport branch's venv
# (werk calls git cherry-pick in the current working directory)
.venv/bin/werk cherry-pick <COMMIT_HASH>
```

If the commit contains no werk files, `werk cherry-pick` behaves identically to `git cherry-pick`.

If the cherry-pick reports conflicts, investigate them before resolving. The most common conflict in this repo is **path conflicts**: the directory layout differs between master and stable branches. For example:

| master path                                                  | 2.5.0 path                            |
| ------------------------------------------------------------ | ------------------------------------- |
| `non-free/packages/cmk-relay-engine/script/install_relay.sh` | `omd/non-free/relay/install_relay.sh` |
| `non-free/packages/cmk-relay-engine/tests/unit-shell/`       | `tests/unit-shell/relay/`             |

For path conflicts on **new files**: git will place the file at the closest matching path it can find. Check that the path is correct for the target branch, and also check that any hardcoded paths _inside_ the file (source paths, shellcheck directives) use the stable-branch layout, not the master layout.

After resolving:

```bash
git add <resolved-files>
git cherry-pick --continue --no-edit
```

### 5. Run formatter, linter, and tests

Run these in parallel where possible, then wait for all results:

```bash
bazel run //:format <CHANGED_FILES>
bazel lint --fix <CHANGED_FILES>
```

For tests, use the appropriate mechanism for the target branch:

- **master**: `bazel test //<package>/...`
- **stable (2.5, 2.4)**: Shell tests are run via `tests/unit-shell/runner.sh <test_file>`, not Bazel, because the `tests/unit-shell/` directories do not have BUILD files.

If the formatter made changes, amend the cherry-pick commit:

```bash
git add <changed-files>
git commit --amend --no-edit
```

### 6. Report

Tell the user:

- The backport branch name
- The commit hash of the cherry-picked commit
- Whether any path conflicts were resolved and what the differences were
- Formatter/linter/test results
