#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Usage: perftest_upload.sh [--site]
#
# Collect the results of the Bazel-based performance suites, or with --site take the site
# suite's, and upload them in CI; see tests/performance/reporting/perftest_run.py.
REPO_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." &>/dev/null && pwd)"
PYTHONPATH="${REPO_PATH}${PYTHONPATH:+:${PYTHONPATH}}" \
    exec python3 -m tests.performance.reporting.perftest_run "${@}"
