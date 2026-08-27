#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Usage: perftest_upload.sh
#
# Collect the results of the Bazel-based performance suites — the tests
# registered in //tests/performance:bazel_performance, run beforehand via
# `bazel test` — from bazel-testlogs into a result directory per suite
# (results/performance-<suite>/<RELEASE>). When running in CI, additionally
# upload each suite to its own performance database (performance_<suite>),
# keeping the suites' scenarios and baselines separate.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_PATH="$(dirname "$(dirname "${SCRIPT_DIR}")")"
BRANCH="$(make --no-print-directory --file="${REPO_PATH}/defines.make" print-BRANCH_VERSION)"
[ "${VERSION}" == "daily" ] && unset VERSION
VERSION="${VERSION:-${BRANCH}-$(date '+%Y.%m.%d')}"
EDITION="${EDITION:-pro}"
RELEASE="${RELEASE:-${VERSION}.${EDITION}}"
TESTLOGS="$(bazel info bazel-testlogs)"
for target in $(bazel query --output=label "tests(//tests/performance:bazel_performance)"); do
    package="${target%:*}"
    suite="$(basename "${package}")"
    suite="${suite#cmk-}"
    testlog_dir="${TESTLOGS}/${package#//}/${target##*:}"
    if [ ! -d "${testlog_dir}/test.outputs" ]; then
        echo "No test outputs for ${target} under ${testlog_dir} - skipping"
        continue
    fi
    ROOT_DIR="${RESULT_PATH:-${REPO_PATH}/results}/performance-${suite}"
    BENCHMARK_DIR="${ROOT_DIR}/${RELEASE}"
    mkdir -p "${BENCHMARK_DIR}"
    cp "${testlog_dir}/test.outputs/"* "${BENCHMARK_DIR}/"
    cp "${testlog_dir}/test.xml" "${BENCHMARK_DIR}/junit.xml"
    if [ -n "${CI}" ]; then
        PLOT_ARGS=(
            --branch-version="${BRANCH}" --root-dir="${ROOT_DIR}"
            --dbname="performance_${suite//-/_}" --dbhost=qa.lan.checkmk.net
            --log-level=INFO --validate-baselines
        )
        # update database; generate report and check weekly baseline
        "${SCRIPT_DIR}/perftest_plot.py" --update "${PLOT_ARGS[@]}" || exit 200
        if [[ "$(date '+%Y-%m-%d')" > "2025-12-01" ]]; then
            # check monthly baseline
            "${SCRIPT_DIR}/perftest_plot.py" "${PLOT_ARGS[@]}" \
                --skip-filesystem-writes --skip-database-writes --baseline-offset=30 || exit 200
        fi
        if [[ "$(date '+%Y-%m-%d')" > "2026-11-01" ]]; then
            # check yearly baseline
            "${SCRIPT_DIR}/perftest_plot.py" "${PLOT_ARGS[@]}" \
                --skip-filesystem-writes --skip-database-writes --baseline-offset=365 || exit 200
        fi
    fi
    echo "ROOT_DIR=${ROOT_DIR}"
done
