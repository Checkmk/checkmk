#!/bin/bash
# PostToolUse hook (SYNC): auto-format files after Edit/Write.
#
# This hook runs SYNCHRONOUSLY — it blocks Claude until formatting is done
# (~1-3s with warm Bazel cache). Synchronous execution is necessary because
# Claude must see the formatted file contents before making the next edit,
# otherwise it would build on top of unformatted code.
#
# Handles all file types supported by bazel run //:format (Python, JS, TS,
# TOML, Shell, CSS, Markdown, etc.). Same command as the pre-commit format
# hook — when new formatters are added, both systems pick them up.
#
# Uses --noblock_for_lock so formatting skips instantly when the Bazel server
# is busy (e.g. async lint running). Without this, formatting would block for
# up to 30s waiting for the Bazel server lock, causing priority inversion
# where a background lint starves the interactive format. Skipped files are
# caught by pre-commit at commit time.
#
# This hook provides fast feedback, not a safety net. The authoritative
# check is the pre-commit format hook which runs at commit time.
set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]] && exit 0

# shellcheck source=.pre-commit-scripts/lib-precommit
source "$(cd "$(dirname "$0")/../.." && pwd)/.pre-commit-scripts/lib-precommit"
[[ ! -f "${GIT_ROOT}/MODULE.bazel" ]] && exit 0

REL_PATH="${FILE_PATH#"${GIT_ROOT}/"}"
cd "$GIT_ROOT"

bazel --noblock_for_lock run //:format -- "$REL_PATH" 2>/dev/null || true

exit 0
