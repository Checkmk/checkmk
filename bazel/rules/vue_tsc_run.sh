#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -uo pipefail

exit_code_file="$1"
shift

"$@"
exit_code=$?

# tsc exits 2 when it found type errors but completed the check.
case "$exit_code" in
    0 | 2) printf '%s' "$exit_code" >"$exit_code_file" ;;
    *)
        cat "$JS_BINARY__STDOUT_OUTPUT_FILE" "$JS_BINARY__STDERR_OUTPUT_FILE" >&2
        exit "$exit_code"
        ;;
esac
