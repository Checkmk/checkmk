#!/usr/bin/env bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_PATH="$(cd "$SCRIPT_DIR/../../.." && pwd)"

SOURCE_DIRS=(cmk non-free omd packages agents)

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

RUN=false
GENERATE_HTML=false
UPLOAD_MODE=""
ALIAS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --run)
            RUN=true
            shift
            ;;
        --generate-html)
            GENERATE_HTML=true
            shift
            ;;
        --upload-totals)
            UPLOAD_MODE="totals"
            shift
            ;;
        --upload-per-module)
            UPLOAD_MODE="per-module"
            shift
            ;;
        --help | -h)
            echo "Usage: $0 [--run] [--generate-html] [--upload-totals|--upload-per-module [alias]]"
            echo ""
            echo "  --run                    Run bazel coverage"
            echo "  --generate-html          Generate HTML report from coverage data"
            echo "  --upload-totals [alias]  Upload aggregate totals to DB"
            echo "  --upload-per-module [alias]  Upload totals and per-module data to DB"
            echo ""
            echo "  --upload-* require: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, QA_POSTGRES_USER, QA_POSTGRES_PASSWORD"
            exit 0
            ;;
        -*)
            echo "Error: Unknown option '$1'" >&2
            echo "Run '$0 --help' for usage." >&2
            exit 1
            ;;
        *)
            ALIAS="$1"
            shift
            ;;
    esac
done

if [[ "$RUN" == false && "$GENERATE_HTML" == false && -z "$UPLOAD_MODE" ]]; then
    echo "Error: no operation specified. Use --run, --generate-html, --upload-totals, or --upload-per-module." >&2
    echo "Run '$0 --help' for usage." >&2
    exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
ALIAS="${ALIAS:-test-unit-all-coverage-${BRANCH}}"

# ---------------------------------------------------------------------------
# Fail fast: validate all upload prerequisites before doing any work
# ---------------------------------------------------------------------------

if [[ -n "$UPLOAD_MODE" ]]; then
    TRACKED_BRANCHES=(master main)
    if [[ ! " ${TRACKED_BRANCHES[*]} " == *" ${BRANCH} "* ]] && [[ ! "$BRANCH" =~ ^[0-9]+\.[0-9]+ ]]; then
        echo "Error: branch '$BRANCH' is not tracked in the coverage database." >&2
        echo "Upload is only supported for master and release branches (e.g. 2.4.0)." >&2
        exit 1
    fi

    REQUIRED_VARS=(POSTGRES_HOST POSTGRES_PORT POSTGRES_DB QA_POSTGRES_USER QA_POSTGRES_PASSWORD)
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            echo "Error: Environment variable $var is not set." >&2
            exit 1
        fi
    done

    read -r COMMIT_HASH COMMIT_DATE COMMIT_TIME COMMIT_TZ _ <<< \
        "$(git log --first-parent --pretty=format:'%h %ci %s' "$BRANCH" | head -1)"
    COMMIT_TIME="${COMMIT_DATE}T${COMMIT_TIME}${COMMIT_TZ}"
    if ! date -d "$COMMIT_TIME" >/dev/null 2>&1; then
        echo "Error: Invalid COMMIT_TIME format: $COMMIT_TIME" >&2
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Prepare and activate venv — mirrors scripts/run-uvenv behaviour
# ---------------------------------------------------------------------------
make --silent -C "$REPO_PATH" .venv 1>&2
# shellcheck source=/dev/null
source "$REPO_PATH/.venv/bin/activate"

# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------

cd "$REPO_PATH"

COVERAGE_DAT="bazel-out/_coverage/_coverage_report.dat"
COVERAGE_FILTERED_DAT="bazel-out/_coverage/_coverage_report_filtered.dat"
COVERAGE_HTML_DIR="results/coverage"
RESULT_CSV="$COVERAGE_HTML_DIR/coverage.csv"

if [[ "$RUN" == true || "$GENERATE_HTML" == true ]]; then
    bazel_env_path="$(bazel run //bazel/tools:bazel_env print-path)"
    export PATH="$PATH:$bazel_env_path"
fi

if [[ "$RUN" == true ]]; then
    filter=$(
        IFS='|'
        echo "${SOURCE_DIRS[*]}"
    )
    bazel coverage //... \
        --cmk_edition=ultimate \
        --test_tag_filters=-component,-cpp,-requires-git \
        --keep_going \
        --build_tests_only \
        --combined_report=lcov \
        --nocache_test_results \
        --instrumentation_filter="//(${filter})[/:@]"
    # Strip the repo root prefix so paths are workspace-relative
    sed -i "s|^SF:${REPO_PATH}/|SF:|g" "$COVERAGE_DAT"
    lcov --extract "$COVERAGE_DAT" \
        "${SOURCE_DIRS[@]/%//*.py}" \
        --output-file "$COVERAGE_FILTERED_DAT"
    lcov --remove "$COVERAGE_FILTERED_DAT" \
        '*/.cache/bazel/*' '*/tests/*' 'tests/*' \
        --output-file "$COVERAGE_FILTERED_DAT"
    "$SCRIPT_DIR/add_missing_coverage.py" \
        --coverage-file "$COVERAGE_FILTERED_DAT" \
        "${SOURCE_DIRS[@]}"
fi

if [[ "$GENERATE_HTML" == true ]]; then
    if [ ! -f "$COVERAGE_FILTERED_DAT" ]; then
        echo "Error: Coverage data file not found at $COVERAGE_FILTERED_DAT" >&2
        exit 1
    fi
    genhtml --title "Checkmk Unit Test Coverage" \
        --quiet \
        --output "$COVERAGE_HTML_DIR" \
        "$COVERAGE_FILTERED_DAT"
fi

if [[ -n "$UPLOAD_MODE" ]]; then
    if [ ! -f "$COVERAGE_FILTERED_DAT" ]; then
        echo "Error: Coverage data file not found at $COVERAGE_FILTERED_DAT" >&2
        exit 1
    fi

    mkdir -p "$COVERAGE_HTML_DIR"
    "$SCRIPT_DIR/code_coverage_summary.py" -i "$COVERAGE_FILTERED_DAT" -o "$RESULT_CSV"
    if [ ! -f "$RESULT_CSV" ]; then
        echo "Error: $RESULT_CSV not created." >&2
        exit 1
    fi

    [[ "$UPLOAD_MODE" == "per-module" ]] && PER_FILE_OPT="--include-module-data" || PER_FILE_OPT=""

    echo "Uploading coverage for commit $COMMIT_HASH at $COMMIT_TIME (mode: $UPLOAD_MODE, alias: $ALIAS)"
    # shellcheck disable=SC2086
    "$SCRIPT_DIR/store_code_coverage.py" \
        --csv-file "$RESULT_CSV" \
        --makefile-target test-unit-all-coverage \
        --alias "$ALIAS" \
        --git-commit-hash "$COMMIT_HASH" \
        --commit-time "$COMMIT_TIME" \
        ${PER_FILE_OPT}
fi
