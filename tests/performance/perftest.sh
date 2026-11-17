#!/usr/bin/env bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_PATH="$(dirname "$(dirname "${SCRIPT_DIR}")")"

BRANCH="$(make --no-print-directory --file="${REPO_PATH}/defines.make" print-BRANCH_VERSION)"
[ "${VERSION}" == "daily" ] && unset VERSION
# exported for the tests and for perftest_upload.sh, so both agree on the release
export VERSION="${VERSION:-${BRANCH}-$(date '+%Y.%m.%d')}"
export EDITION="${EDITION:-cee}"
RELEASE="${RELEASE:-${VERSION}.${EDITION}}"
BENCHMARK_DIR="${RESULT_PATH:-${REPO_PATH}/results}/performance/${RELEASE}"
mkdir -p "${BENCHMARK_DIR}"
pytest "${SCRIPT_DIR}/system" \
    --benchmark-json="${BENCHMARK_DIR}/benchmark.json" \
    --benchmark-verbose --html="${BENCHMARK_DIR}/report.htm" \
    --self-contained-html --ignore-running-procs \
    --log-level=INFO --log-cli-level=INFO "${@}"
RC=$?
"${SCRIPT_DIR}/perftest_upload.sh" --site || exit $?
exit "$RC"
