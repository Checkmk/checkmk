#!/bin/bash
# PostToolUse hook (ASYNC): debounced Bazel lint after Edit/Write.
#
# This hook runs ASYNCHRONOUSLY — it does not block Claude. Async execution
# is required because bazel lint takes 5-30s per package. Running it
# synchronously would turn a 2-3s editing sequence into a 2-minute wait.
# Instead, Claude continues editing while lint results arrive later as
# system messages.
#
# Condition for making this sync: if Bazel supported per-file lint without
# full package analysis (no dependency graph walk), or if the lint toolchain
# ran outside Bazel's single-server lock, lint could complete in <2s and
# run synchronously like format. Until then, it must be async.
#
# Batching via flock:
# Claude makes rapid sequential edits. Without batching, each edit spawns a
# separate bazel lint invocation. Bazel's single server serializes them,
# so N edits = N * (startup + lint) time, each holding the server and
# blocking the sync format hook. The flock + pending file pattern batches
# files: only one bazel lint runs at a time, and files that arrive during
# a lint run accumulate in the pending list for the next batch. This
# minimizes Bazel server hold time and prevents races on the pending file.
#
# Bazel server contention:
# The sync format hook and this async lint hook both use the Bazel server.
# To reduce priority inversion (lint blocking format), this hook waits
# via --noblock_for_lock until the server is free before starting, and the
# format hook skips instantly if the server is busy. Format has scheduling
# priority — lint waits for the server to be free before starting — but
# once lint is running, format skips until it finishes.
#
# Report-only (no --fix):
# Lint runs without --fix because auto-fixing files while Claude is
# actively editing causes race conditions — Claude's next Edit call
# targets an old_string that no longer matches after lint rewrote the file.
# Claude reads the lint report and fixes issues itself in subsequent edits.
#
# This hook provides early feedback, not a safety net. The authoritative
# check is the pre-commit lint hook which runs at commit time.
set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]] && exit 0

# shellcheck source=.pre-commit-scripts/lib-precommit
source "$(cd "$(dirname "$0")/../.." && pwd)/.pre-commit-scripts/lib-precommit"
[[ ! -f "${GIT_ROOT}/MODULE.bazel" ]] && exit 0

REL_PATH="${FILE_PATH#"${GIT_ROOT}/"}"

# Workspace-specific temp files (safe for multiple repos)
WS_HASH=$(echo "$GIT_ROOT" | md5sum | cut -c1-8)
PENDING="/tmp/claude-lint-pending-${WS_HASH}.txt"
LOCK="/tmp/claude-lint-${WS_HASH}.lock"

# Append this file to the pending list
echo "$REL_PATH" >>"$PENDING"

# Try to acquire lock (non-blocking).
# If another lint holds it, exit — it will pick up our file from pending.
exec 200>"$LOCK"
if ! flock -n 200; then
    exit 0
fi

cd "$GIT_ROOT"

# Wait for the Bazel server to be free before starting lint.
# The sync format hook has priority; we yield until it is done.
for _ in $(seq 1 60); do
    bazel --noblock_for_lock info &>/dev/null && break
    sleep 1
done

# Drain pending files in a loop. New files may arrive while we lint.
while [[ -s "$PENDING" ]]; do
    # Atomically swap pending -> current
    mv "$PENDING" "${PENDING}.current" 2>/dev/null || break
    mapfile -t FILES < <(sort -u "${PENDING}.current")
    rm -f "${PENDING}.current"

    [[ ${#FILES[@]} -eq 0 ]] && break

    # Call the same script pre-commit uses — zero duplication
    .pre-commit-scripts/run-lint-bazel "${FILES[@]}" 2>&1 || true
done

exit 0
