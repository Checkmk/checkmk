#!/usr/bin/env bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The script updates the unit tests code coverage statistics with uploading of
# the statistics into Checkmk's code coverage tracking system.
# The script requires certain environment variables to be set for database connection:
#   POSTGRES_HOST
#   POSTGRES_PORT
#   POSTGRES_DB
#   QA_POSTGRES_USER
#   QA_POSTGRES_PASSWORD
#
# Usage:
#   ./update_code_cov.sh [UPLOAD_MODE] [ALIAS]

set -e

# Get git branch name
BRANCH=$(git rev-parse --abbrev-ref HEAD)

UPLOAD_MODE=${1}
TARGET=test-unit-all-coverage
ALIAS="${2:-${TARGET}-${BRANCH}}"

case "$UPLOAD_MODE" in
    --summary)
        PER_FILE_OPT=
        ;;
    --detailed)
        PER_FILE_OPT=" --include-module-data"
        ;;
    "" | --help | -h)
        echo "The script uploads code coverage statistics to the database."
        echo "Requires the following environment variables to be set:"
        echo "  POSTGRES_HOST"
        echo "  POSTGRES_PORT"
        echo "  POSTGRES_DB"
        echo "  QA_POSTGRES_USER"
        echo "  QA_POSTGRES_PASSWORD"
        echo ""
        echo "Usage: $0 [--summary|--detailed] [alias]"
        echo "  --summary   Upload summary data only"
        echo "  --detailed  Upload summary and detailed module data (includes --include-module-data)"
        echo "  alias       Optional alias for the coverage data test run (default: ${TARGET}-${BRANCH})"
        exit 0
        ;;
    *)
        echo "Error: Unknown option '$UPLOAD_MODE'"
        echo "Usage: $0 [--summary|--detailed] [alias]"
        exit 1
        ;;
esac
echo "Upload mode: ${UPLOAD_MODE} [${PER_FILE_OPT}] , alias: ${ALIAS}, branch: ${BRANCH}"

# Check if required env variables are set
REQUIRED_VARS=("POSTGRES_HOST" "POSTGRES_PORT" "POSTGRES_DB" "QA_POSTGRES_USER" "QA_POSTGRES_PASSWORD")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: Environment variable $var is not set."
        exit 1
    fi
done

# Activate the virtual environment
VENV_PATH="$(dirname "$0")/../../.venv/bin/activate"
if [ ! -f "${VENV_PATH}" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi
# shellcheck source=/dev/null
source "${VENV_PATH}"

# Get last commit info
git pull origin "${BRANCH}"
read -r COMMIT_HASH COMMIT_DATE COMMIT_TIME COMMIT_TZ _ <<< \
    "$(git log --first-parent --pretty=format:'%h %ci %s' "$BRANCH" | head -1)"
COMMIT_TIME="${COMMIT_DATE}T${COMMIT_TIME}${COMMIT_TZ}"

# Validate COMMIT_TIME format
if ! date -d "${COMMIT_TIME}" >/dev/null 2>&1; then
    echo "Error: Invalid COMMIT_TIME format: ${COMMIT_TIME}"
    exit 1
fi

# Run the code coverage update script
BAZEL_COVERAGE_ARGS='--flaky_test_attempts=3 --instrumentation_filter="//(cmk|packages|agents)[/:@]"' make -C tests "${TARGET}"

# Check if coverage data file exists
COVERAGE_DATA_FILE="$(bazel info bazel-testlogs)"/tests/unit/repo/coverage.dat
if [ ! -f "${COVERAGE_DATA_FILE}" ]; then
    echo "Error: Coverage data file not found at ${COVERAGE_DATA_FILE}"
    exit 1
fi

RESULT_CSV="./results/coverage/coverage.csv"
# Convert coverage data to CSV, Assuming the ./results/coverage directory exists after 'bazel coverage'
tests/scripts/code_coverage_summary.py -i "${COVERAGE_DATA_FILE}" -o "${RESULT_CSV}"

if [ ! -f "${RESULT_CSV}" ]; then
    echo "Error: ${RESULT_CSV} not created."
    exit 1
fi

echo "Uploading code coverage for commit ${COMMIT_HASH} at ${COMMIT_TIME}"
set -x
# shellcheck disable=SC2086
tests/scripts/store_code_coverage.py --csv-file "${RESULT_CSV}" --makefile-target "${TARGET}" --alias "${ALIAS}" --git-commit-hash "${COMMIT_HASH}" --commit-time "${COMMIT_TIME}" ${PER_FILE_OPT}
