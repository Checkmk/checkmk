#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Runs cross-compiled Rust test binaries (libtest harness) under Wine;
# shared by the packages' *-tests-wine targets via rust_wine_test().
# Tests needing real Windows are listed in the skip file (one libtest
# --skip substring per line, applied to every binary).
#
# Usage: rust-test-wine.sh <wine> <skip-file> [<prepare> <arg>...] -- <test-exe>...
#
# Everything is staged into a short scratch directory and run from there:
# spawned sibling processes (e.g. cmk-agent-ctl's controller) resolve via
# absolute paths derived from the test's cwd, and CreateProcess rejects
# non-verbatim paths over 260 chars — which both a sandbox runfiles path
# and $TEST_TMPDIR (it lives under the sandbox execroot) exceed. /tmp is
# short, action-private under the sandbox's hermetic /tmp, and cleaned up
# by the trap for unsandboxed runs.
#
# The optional prepare hook runs from the test cwd (so its $(rootpath)
# arguments resolve) with $WINE and $SCRATCH exported, after the Wine
# prefix is set up and before the binaries run.

set -euo pipefail

if [ "$#" -lt 4 ]; then
    echo "usage: $0 <wine> <skip-file> [<prepare> <arg>...] -- <test-exe>..." >&2
    exit 64
fi
# Set by bazel test; the WINEPREFIX below must not land anywhere durable.
: "${TEST_TMPDIR:?this runner expects to be invoked via bazel test}"

WINE_FROM_RUNFILES="$1" # @wine_linux_x86_64//:wine_bin (rootpath)
SKIP_FILE="$2"
shift 2

PREPARE=""
PREPARE_ARGS=()
while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do
    if [ -z "$PREPARE" ]; then
        PREPARE="$1"
    else
        PREPARE_ARGS+=("$1")
    fi
    shift
done
if [ "$#" -eq 0 ]; then
    echo "error: missing -- separator before the test executables" >&2
    exit 64
fi
shift # the -- separator

# Precedence: an explicit WINE env override (dev/debug) wins; otherwise use
# the hermetic wine staged in runfiles; only then fall back to PATH.
if [ -z "${WINE:-}" ] && [ -n "$WINE_FROM_RUNFILES" ]; then
    WINE="$(realpath "$WINE_FROM_RUNFILES")"
fi
WINE="${WINE:-$(command -v wine64 || command -v wine || true)}"
if [ -z "$WINE" ]; then
    echo "error: wine not found." >&2
    echo "       This normally comes from @wine_linux_x86_64 in runfiles;" >&2
    echo "       to override, run with --test_env=WINE=/path/to/wine64." >&2
    exit 1
fi

# Never touch the user's ~/.wine; a fresh prefix initializes in seconds.
export WINEPREFIX="${TEST_TMPDIR}/wineprefix"
# Run headless even on a desktop: with a display reachable, winex11/winewayland
# would connect to it (and can flash windows or pull in GUI state).
unset DISPLAY WAYLAND_DISPLAY
export WINEDEBUG="${WINEDEBUG:--all}"
# Backtraces in the CI log on panic; free when everything passes.
export RUST_BACKTRACE="${RUST_BACKTRACE:-1}"

SKIPS=()
while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in "" | "#"*) continue ;; esac
    SKIPS+=(--skip "$line")
done <"$SKIP_FILE"

SCRATCH=$(mktemp -d -p /tmp rust-wine.XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT
export WINE SCRATCH

if [ -n "$PREPARE" ]; then
    bash "$PREPARE" ${PREPARE_ARGS[@]+"${PREPARE_ARGS[@]}"}
fi

rc=0
for exe in "$@"; do
    echo "=== $exe"
    cp -L "$exe" "$SCRATCH/"
    (cd "$SCRATCH" && "$WINE" "./$(basename "$exe")" --test-threads=1 \
        ${SKIPS[@]+"${SKIPS[@]}"}) || rc=1
done
exit "$rc"
