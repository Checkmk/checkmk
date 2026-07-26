#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Runs the cross-compiled watest.exe under Wine with the repo's unit tier
# filter (run_tests.ps1) plus the Wine-specific exclusions from
# wine-excluded-tests.txt. The Component/Simulation tiers need real Windows,
# there as here.

set -euo pipefail

EXCLUDE_FILE="$1"
EXE="$2"
WINE="$(realpath "$3")" # @wine_linux_x86_64//:wine_bin (rootpath)

# Run headless even on a desktop: with a display reachable, winex11/winewayland
# would connect to it (and can flash windows or pull in GUI state).
unset DISPLAY WAYLAND_DISPLAY

# Never touch the user's ~/.wine; a fresh prefix initializes in seconds.
export WINEPREFIX="${TEST_TMPDIR}/wineprefix"
export WINEDEBUG="${WINEDEBUG:--all}"

# Strip CRs (Windows edits) and surrounding whitespace, drop comment and blank
# lines, then colon-join. sed/paste stay silent on empty input, so a
# comment-only file yields an empty EXCLUDES without tripping set -e/pipefail.
EXCLUDES=$(sed -e 's/\r$//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
    -e '/^#/d' -e '/^$/d' "$EXCLUDE_FILE" | paste -sd: -)

# Append the extra exclusions only when non-empty, so we never emit a dangling
# ':' (an empty gtest pattern) at the end of the negative filter.
FILTER="-*_Simulation:*Component:*ComponentExt:*Flaky"
if [ -n "$EXCLUDES" ]; then
    FILTER="${FILTER}:${EXCLUDES}"
fi

exec "$WINE" "$EXE" "--gtest_filter=${FILTER}"
