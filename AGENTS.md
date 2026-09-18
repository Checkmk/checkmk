# AI Agent Instructions

## Build & Test

**NEVER run `pytest`, `ruff`, or `mypy` directly.** Always use `bazel` commands
instead. Direct invocations bypass the build system's environment and dependency
setup and produce incorrect results.

Bazel is the primary build system for unit tests, linting, formatting, and type
checking. System tests use run_tests.sh:

```
tests/run_tests.sh test-system-singlesite
tests/run_tests.sh test-system-multisite
tests/run_tests.sh test-system-gui
```

Always format, lint, and run tests after completing a task.
Use `bazel run //:format <PATHS>` to format and `bazel lint --fix` to autofix lint findings.
Report any remaining non-autofixable findings (including mypy) to the user.

See [BAZEL.md](BAZEL.md) for the full developer command reference.

## Python Conventions

- Python version per `pyproject.toml`; type hints required; pathlib over os.path
- Formatting/linting via `bazel lint` (ruff); type checking via `bazel build --config=mypy` (mypy)
- Agent plugins: Python 3.4+ compatible
- GUI cannot import cmk/base internals (enforced by component isolation)

## Testing

Read [TESTING.md](TESTING.md) before writing, changing, or debugging tests, and
run its self-check before finishing. It defines the test levels and their
directories, the flaky-test process, and the core rules: test through the
public surface, inject dependencies instead of patching Checkmk code, one
behavior per test.

## Editions

The codebase supports five editions: `community`, `pro`, `ultimate`,
`ultimatemt`, `cloud`. The active edition controls which `cmk` targets and
Python modules are available; pass `--cmk_edition=<edition>` to Bazel.

## Skills & Agents

Reusable AI workflows for this repo (code review, werk authoring,
Gerrit/Jenkins/Jira/crash-report helpers, backports, etc.) are maintained as
Claude Code plugins in the internal marketplace repository:
https://github.com/Checkmk/checkmk-claude-marketplace

Notable entry points:

- [`code-review` agent](https://github.com/Checkmk/checkmk-claude-marketplace/blob/main/plugins/checkmk-core/agents/code-review.md)
  — after committing a change (or a relation chain of commits), consider
  running it, or propose doing so, to catch logical, semantic, and
  architectural issues before pushing for review.
- [`/test-review` skill](https://github.com/Checkmk/checkmk-claude-marketplace/blob/main/plugins/checkmk-core/skills/test-review/SKILL.md)
  — run it whenever implementing or changing tests.

Do not add skills or agents under `.claude/` or `.github/` in this repo —
contribute them to the marketplace instead.

## Commit rules

Before a commit do a sanity check of your changes and run the linters and formatters.

### Files that must never be committed

Ensure the following paths are NOT part of any commit (check `git status` /
`git diff --cached` before committing and unstage them if they appear):

- `tests/qa-test-data` (submodule — never update its pinned commit)
