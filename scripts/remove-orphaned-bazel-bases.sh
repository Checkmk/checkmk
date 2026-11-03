#!/usr/bin/env bash
# Garbage-collect Bazel state left behind by deleted worktrees.
#
# Removes every Bazel output base whose workspace directory no longer exists
# (same teardown as .paseo/reclaim-bazel-output-base.sh, but for orphans).
# Since the workspace is gone, a still running server is stopped via the pid
# recorded in its output base instead of `bazel shutdown`.
#
# Usage: remove-orphaned-bazel-bases.sh [--dry-run]
#   --dry-run  only print what would be removed
set -u

dry_run=0
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) dry_run=1 ;;
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
    shift
done

base_root="${HOME}/.cache/bazel/_bazel_${USER}"

run() {
    if [ "$dry_run" -eq 1 ]; then echo "[dry-run] $*"; else "$@"; fi
}

stop_server() {
    local base="$1" pid
    pid="$(cat "$base/server/server.pid.txt" 2>/dev/null)"
    [ -n "$pid" ] || return 0
    # Guard against a stale pid that was reused by an unrelated process
    [ -r "/proc/$pid/cmdline" ] || return 0
    tr '\0' '\n' <"/proc/$pid/cmdline" | grep -qxF -- "--output_base=$base" || return 0
    echo "stopping bazel server $pid"
    run kill "$pid"
    [ "$dry_run" -eq 1 ] && return 0
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        kill -0 "$pid" 2>/dev/null || return 0
        sleep 1
    done
    echo "bazel server $pid did not exit after SIGTERM" >&2
}

total_mb=0
for base in "$base_root"/*/; do
    base="${base%/}"
    marker="$base/DO_NOT_BUILD_HERE"
    [ -f "$marker" ] || continue # skips cache/ and install/
    workspace="$(cat "$marker" 2>/dev/null)"
    [ -n "$workspace" ] || continue # unknown owner, leave it alone
    [ -d "$workspace" ] && continue # worktree still exists

    size_mb="$(du -sm "$base" 2>/dev/null | cut -f1)"
    echo "orphan: $base (${size_mb:-?}M) <- $workspace"
    stop_server "$base"
    # rules_js leaves read-only pnpm dirs, so restore write perms first
    run chmod -R u+w "$base"
    run rm -rf "$base"
    if [ "$dry_run" -eq 1 ]; then
        total_mb=$((total_mb + ${size_mb:-0}))
    elif [ ! -e "$base" ]; then
        total_mb=$((total_mb + ${size_mb:-0}))
    else
        echo "failed to remove $base" >&2
    fi
done
if [ "$dry_run" -eq 1 ]; then
    echo "would free: ${total_mb}M"
else
    echo "freed: ${total_mb}M"
fi
