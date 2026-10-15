#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -euo pipefail

exit_code_file="$1"
log_file="$2"
stderr_file="$3"
passed_file="$4"

cat "$log_file" "$stderr_file" >&2
exit_code="$(cat "$exit_code_file")"
if [ "$exit_code" != 0 ]; then
    exit "$exit_code"
fi
touch "$passed_file"
