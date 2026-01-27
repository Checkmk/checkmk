#!/usr/bin/env bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_PATH="$(dirname "$(dirname "${SCRIPT_DIR}")")"
BRANCH="$(make --no-print-directory --file="${REPO_PATH}/defines.make" print-BRANCH_VERSION)"
[ "${VERSION}" == "daily" ] && unset VERSION
export VERSION="${VERSION:-${BRANCH}-$(date '+%Y.%m.%d')}"
export EDITION="${EDITION:-cee}"
RELEASE="${RELEASE:-${VERSION}.${EDITION}}"
ROOT_DIR="${RESULT_PATH:-${REPO_PATH}/results}/performance"
BENCHMARK_DIR="${ROOT_DIR}/${RELEASE}"
mkdir -p "${BENCHMARK_DIR}"
pytest "${SCRIPT_DIR}" \
    --benchmark-json="${BENCHMARK_DIR}/benchmark.json" \
    --benchmark-verbose --html="${BENCHMARK_DIR}/report.htm" \
    --self-contained-html --ignore-running-procs "${@}"
RC=$?
if [ -n "${CI}" ]; then
    # update database; generate report and check weekly baseline
    "${SCRIPT_DIR}/perftest_plot.py" --update \
        --root-dir="${ROOT_DIR}" --log-level=INFO --dbhost=qa.lan.checkmk.net \
        --validate-baselines --alert-on-failure --jira-url="https://jira.lan.tribe29.com/" || exit 200
    if [[ "$(date '+%Y-%m-%d')" > "2025-12-01" ]]; then
        # check monthly baseline
        "${SCRIPT_DIR}/perftest_plot.py" \
            --root-dir="${ROOT_DIR}" --log-level=INFO --dbhost=qa.lan.checkmk.net \
            --validate-baselines --alert-on-failure --jira-url="https://jira.lan.tribe29.com/" \
            --skip-filesystem-writes --skip-database-writes --baseline-offset=30 || exit 200
    fi
    if [[ "$(date '+%Y-%m-%d')" > "2026-11-01" ]]; then
        # check yearly baseline
        "${SCRIPT_DIR}/perftest_plot.py" \
            --root-dir="${ROOT_DIR}" --log-level=INFO --dbhost=qa.lan.checkmk.net \
            --validate-baselines --alert-on-failure --jira-url="https://jira.lan.tribe29.com/" \
            --skip-filesystem-writes --skip-database-writes --baseline-offset=365 || exit 200
    fi
fi
echo "ROOT_DIR=${ROOT_DIR}"
exit "$RC"
