#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Usage: perftest_upload.sh [--site]
#
# Without arguments, collect the results of the Bazel-based performance suites
# (the tests registered in //tests/performance:bazel_performance, run beforehand
# via `bazel test`) from bazel-testlogs into a result directory per suite
# (results/performance-<suite>/<RELEASE>). When running in CI, additionally
# upload each suite to its performance database: the data backend to its own,
# every other (component) suite to performance_component.
#
# With --site, upload the site suite's results, which perftest.sh leaves in
# results/performance/<RELEASE>, to the performance database. Its baseline
# checks only warn.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_PATH="$(dirname "$(dirname "${SCRIPT_DIR}")")"

# perftest_plot.py imports the rest of the reporting as tests.performance.reporting, so it runs
# as a module from the repository root.
perftest_plot() {
    PYTHONPATH="${REPO_PATH}${PYTHONPATH:+:${PYTHONPATH}}" python3 -m tests.performance.reporting.perftest_plot "$@"
}

# upload <root_dir> <database> [plot options]
# In CI, write a suite's results to its database, generate the report and check the weekly,
# monthly and yearly baselines. The plot options go to all three calls. Returns 200 if any of
# them failed, after running all three.
upload() {
    local root_dir="$1" database="$2" rc=0
    shift 2
    [ -n "${CI}" ] || return 0
    local plot_args=(
        --branch-version="${BRANCH}" --product-release="${VERSION}" --root-dir="${root_dir}"
        --dbname="${database}" --dbhost=qa.lan.checkmk.net --require-database
        --log-level=INFO --validate-baselines "$@"
    )
    # write to the database; generate report and check weekly baseline
    perftest_plot "${plot_args[@]}" || rc=200
    # check monthly baseline
    perftest_plot "${plot_args[@]}" \
        --skip-filesystem-writes --skip-database-writes --baseline-offset=30 || rc=200
    # check yearly baseline
    perftest_plot "${plot_args[@]}" \
        --skip-filesystem-writes --skip-database-writes --baseline-offset=365 || rc=200
    return "${rc}"
}

BRANCH="$(make --no-print-directory --file="${REPO_PATH}/defines.make" print-BRANCH_VERSION)"
[ "${VERSION}" == "daily" ] && unset VERSION
VERSION="${VERSION:-${BRANCH}-$(date '+%Y.%m.%d')}"
EDITION="${EDITION:-cee}"
RELEASE="${RELEASE:-${VERSION}.${EDITION}}"

if [ "$1" == "--site" ]; then
    ROOT_DIR="${RESULT_PATH:-${REPO_PATH}/results}/performance"
    upload "${ROOT_DIR}" performance --warn-only
    RC=$?
    echo "ROOT_DIR=${ROOT_DIR}"
    exit "${RC}"
fi

# A suite's failed upload or baseline check fails the job, but only after every suite is uploaded.
RC=0

TESTLOGS="$(bazel info bazel-testlogs)"
for target in $(bazel query --output=label "tests(//tests/performance:bazel_performance)"); do
    package="${target%:*}"
    suite="$(basename "${package}")"
    suite="${suite#cmk-}"
    case "${suite}" in
        data-backend) database="performance_data_backend" ;;
        # The default. A suite that needs another database gets its own entry here.
        *) database="performance_component" ;;
    esac
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
    # add this suite to the release's job
    upload "${ROOT_DIR}" "${database}" --append-db || RC=200
    echo "ROOT_DIR=${ROOT_DIR}"
done
exit "${RC}"
