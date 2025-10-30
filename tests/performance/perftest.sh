#!/usr/bin/env bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
[ -z "${BENCHMARK_DIR}" ] && echo "ERROR: BENCHMARK_DIR not defined!"
[ -z "${ROOT_DIR}" ] && echo "ERROR: ROOT_DIR not defined!"
mkdir -p "${BENCHMARK_DIR}"
pytest "$(realpath performance)" \
    --benchmark-json="${BENCHMARK_DIR}/benchmark.json" \
    --benchmark-verbose --html="${BENCHMARK_DIR}/report.htm" \
    --self-contained-html --ignore-running-procs || exit 1
# update database; generate report and check weekly baseline
"$(realpath performance)/perftest_plot.py" --update \
    --root-dir="${ROOT_DIR}" --log-level=INFO --dbhost=qa.lan.checkmk.net \
    --validate-baselines --alert-on-failure --jira-url="https://jira.lan.tribe29.com/" || exit 2
if [ "$(date '+%Y-%m-%d')" -ge "2025-12-01" ]; then
    # check monthly baseline
    "$(realpath performance)/perftest_plot.py" \
        --root-dir="${ROOT_DIR}" --log-level=INFO --dbhost=qa.lan.checkmk.net \
        --validate-baselines --alert-on-failure --jira-url="https://jira.lan.tribe29.com/" \
        --skip-filesystem-writes --skip-database-writes --baseline-offset=30 || exit 2
fi
if [ "$(date '+%Y-%m-%d')" -ge "2026-11-01" ]; then
    # check yearly baseline
    "$(realpath performance)/perftest_plot.py" \
        --root-dir="${ROOT_DIR}" --log-level=INFO --dbhost=qa.lan.checkmk.net \
        --validate-baselines --alert-on-failure --jira-url="https://jira.lan.tribe29.com/" \
        --skip-filesystem-writes --skip-database-writes --baseline-offset=365 || exit 2
fi
