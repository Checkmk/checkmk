---
name: bazel
description: Guide for running Bazel tests and linting in the Checkmk codebase.
---

# Running Tests

## Execution & Filtering

```bash
# Run all tests in a package (recursive with /...)
bazel test //packages/cmk-messaging/...
# Run specific target
bazel test //packages/cmk-messaging:unit
# Filter specific tests (regex supported)
bazel test //packages/cmk-messaging:unit --test_filter="test_connection*"
bazel test //packages/...:all --test_filter=".*integration.*"
```

## Output & Debugging

```bash
# Output: all (verbose), errors (concise), summary
bazel test //packages/cmk-messaging:unit --test_output=errors
# Detailed summary
bazel test //packages/... --test_summary=detailed
# Reproduce flakes (run 100x, stop on failure)
bazel test //packages/cmk-messaging:unit \
  --runs_per_test=100 \
  --runs_per_test_detects_flakes \
  --test_output=streamed
```

## Discovery

```bash
bazel query 'tests(//packages/cmk-messaging/...)'
```

# Linting

## Standard Linters

```bash
# Run all linters (interactive by default)
bazel lint //packages/cmk-messaging:all
# Common options
bazel lint --fix //packages/...    # Auto-apply fixes
bazel lint --diff //packages/...   # Show diffs
bazel lint --quiet //packages/...  # Show only issues
```

## Specific Checks

```bash
# Mypy (Type Checking)
bazel build --config=mypy //packages/cmk-messaging:all
# Clippy (Rust)
bazel build --config=clippy //packages/cmk-agent-ctl:all
```
