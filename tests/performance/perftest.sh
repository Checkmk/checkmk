#!/usr/bin/env bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Run the site suite, whose conftest writes the results into the run's folder, and upload them.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
# The run's day, for the tests and the upload alike, even if the run ends after midnight.
export PERFTEST_DATE="${PERFTEST_DATE:-$(date '+%Y-%m-%d')}"
pytest "${SCRIPT_DIR}/system" \
    --benchmark-verbose --self-contained-html --ignore-running-procs \
    --log-level=INFO --log-cli-level=INFO "${@}"
RC=$?
"${SCRIPT_DIR}/perftest_upload.sh" --site || exit $?
exit "$RC"
