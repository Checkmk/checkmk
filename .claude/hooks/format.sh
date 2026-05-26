#!/bin/bash
# PostToolUse hook (SYNC): auto-format files after Edit/Write.
#
# This hook runs SYNCHRONOUSLY — it blocks Claude until formatting is done.
# Synchronous execution is necessary because Claude must see the formatted
# file contents before making the next edit, otherwise it would build on
# top of unformatted code.
#
# Handles all file types supported by bazel run //:format (Python, JS, TS,
# TOML, Shell, CSS, Markdown, etc.). Same command as the pre-commit format
# hook — when new formatters are added, both systems pick them up.
#
# Loud on failure: bazel's exit code propagates and the hook exits 2 so
# Claude Code surfaces the bazel output to the agent as a tool error.
# This replaces the previous --noblock_for_lock + 2>/dev/null || true
# pattern, which silently dropped files whenever the Bazel server was
# busy and let unformatted code reach Gerrit.
set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]] && exit 0

# shellcheck source=.pre-commit-scripts/lib-precommit
source "$(cd "$(dirname "$0")/../.." && pwd)/.pre-commit-scripts/lib-precommit"
[[ ! -f "${GIT_ROOT}/MODULE.bazel" ]] && exit 0

REL_PATH="${FILE_PATH#"${GIT_ROOT}/"}"
cd "$GIT_ROOT"

# `timeout 60` so a wedged Bazel server (cold cache, hung lock, OOM)
# doesn't strand the session — every subsequent Edit would otherwise
# block on the same server. 124 = timeout's default timeout exit.
rc=0
timeout 60 bazel run //:format -- "$REL_PATH" >&2 || rc=$?
if [[ $rc -ne 0 ]]; then
    if [[ $rc -eq 124 ]]; then
        echo "format hook: timed out after 60s for $REL_PATH (Bazel server stuck?)" >&2
    else
        echo "format hook: bazel run //:format failed for $REL_PATH" >&2
    fi
    exit 2
fi
