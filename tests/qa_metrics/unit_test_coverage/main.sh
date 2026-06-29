#!/usr/bin/env bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_PATH="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"

# Operate from the repo root for the rest of the script: the git metadata
# queries below and bazel (which locates the workspace from the working
# directory) all need to run inside the workspace.
cd "$REPO_PATH"

SOURCE_DIRS=(cmk non-free omd packages agents)
# Top-level dirs that contain Python but are intentionally excluded from
# coverage (the tests themselves, tooling, docs).
NON_SOURCE_DIRS=(tests doc scripts buildscripts bin bazel .ide)

# Guard against silent drift: every top-level dir that ships tracked Python
# must be classified as source or non-source. A new or renamed one surfaces
# here as an error instead of quietly skewing the coverage number.
known_dirs=$(printf '%s\n' "${SOURCE_DIRS[@]}" "${NON_SOURCE_DIRS[@]}" | sort -u)
actual_dirs=$(git ls-files '*.py' | sed 's#/.*##' | sort -u)
unclassified=$(comm -23 <(printf '%s\n' "$actual_dirs") <(printf '%s\n' "$known_dirs"))
if [[ -n "$unclassified" ]]; then
    echo "Error: top-level dir(s) with Python not classified as source/non-source:" >&2
    echo "  ${unclassified//$'\n'/$'\n'  }" >&2
    echo "Add each to SOURCE_DIRS or NON_SOURCE_DIRS in ${BASH_SOURCE[0]}." >&2
    exit 1
fi

# Every tool is invoked through `bazel run` so Bazel provides it hermetically --
# no venv activation, no PATH manipulation. The edition flag is passed to every
# bazel command (not just `bazel coverage`) so they all share one build
# configuration and don't thrash the analysis cache.
EDITION_FLAG="--cmk_edition=ultimate"
PKG="//tests/qa_metrics/unit_test_coverage"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

RUN=false
GENERATE_HTML=false
UPLOAD_TOTALS=false
UPLOAD_PER_MODULE=false

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
            UPLOAD_TOTALS=true
            shift
            ;;
        --upload-per-module)
            UPLOAD_PER_MODULE=true
            shift
            ;;
        --help | -h)
            echo "Usage: $0 [--run] [--generate-html] [--upload-totals] [--upload-per-module]"
            echo ""
            echo "  --run                  Run bazel coverage"
            echo "  --generate-html        Generate HTML report from coverage data"
            echo "  --upload-totals        Upload overall coverage to the history table"
            echo "  --upload-per-module    Rewrite the per-module coverage table"
            echo ""
            echo "The flags combine freely, e.g. '--run --upload-totals --upload-per-module'"
            echo "runs coverage and uploads both. At least one flag is required."
            echo ""
            echo "  --upload-* require: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, QA_POSTGRES_USER, QA_POSTGRES_PASSWORD"
            exit 0
            ;;
        *)
            echo "Error: Unknown argument '$1'" >&2
            echo "Run '$0 --help' for usage." >&2
            exit 1
            ;;
    esac
done

DO_UPLOAD=false
if [[ "$UPLOAD_TOTALS" == true || "$UPLOAD_PER_MODULE" == true ]]; then
    DO_UPLOAD=true
fi

if [[ "$RUN" == false && "$GENERATE_HTML" == false && "$DO_UPLOAD" == false ]]; then
    echo "Error: no operation specified. Use --run, --generate-html, --upload-totals, or --upload-per-module." >&2
    echo "Run '$0 --help' for usage." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Fail fast: validate all upload prerequisites before doing any work
# ---------------------------------------------------------------------------

if [[ "$DO_UPLOAD" == true ]]; then
    REQUIRED_VARS=(POSTGRES_HOST POSTGRES_PORT POSTGRES_DB QA_POSTGRES_USER QA_POSTGRES_PASSWORD)
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            echo "Error: Environment variable $var is not set." >&2
            exit 1
        fi
    done

    read -r COMMIT_HASH COMMIT_DATE COMMIT_TIME COMMIT_TZ _ <<< \
        "$(git log --first-parent --pretty=format:'%h %ci %s' | head -1)"
    COMMIT_TIME="${COMMIT_DATE}T${COMMIT_TIME}${COMMIT_TZ}"
    if ! date -d "$COMMIT_TIME" >/dev/null 2>&1; then
        echo "Error: Invalid COMMIT_TIME format: $COMMIT_TIME" >&2
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------

# File arguments are absolute, since `bazel run` executes its targets in the
# runfiles tree, not in this directory.
COVERAGE_DAT="$REPO_PATH/bazel-out/_coverage/_coverage_report.dat"
COVERAGE_FILTERED_DAT="$REPO_PATH/bazel-out/_coverage/_coverage_report_filtered.dat"
COVERAGE_HTML_DIR="$REPO_PATH/results/coverage"
RESULT_CSV="$COVERAGE_HTML_DIR/coverage.csv"

if [[ "$RUN" == true ]]; then
    filter=$(
        IFS='|'
        echo "${SOURCE_DIRS[*]}"
    )
    bazel coverage //... \
        "$EDITION_FLAG" \
        --test_tag_filters=-component,-cpp,-requires-git \
        --keep_going \
        --build_tests_only \
        --combined_report=lcov \
        --nocache_test_results \
        --instrumentation_filter="//(${filter})[/:@]"
    # Strip the repo root prefix so paths are workspace-relative
    sed -i "s|^SF:${REPO_PATH}/|SF:|g" "$COVERAGE_DAT"
    bazel run @lcov//:lcov "$EDITION_FLAG" -- \
        --extract "$COVERAGE_DAT" \
        "${SOURCE_DIRS[@]/%//*.py}" \
        --output-file "$COVERAGE_FILTERED_DAT"
    bazel run @lcov//:lcov "$EDITION_FLAG" -- \
        --remove "$COVERAGE_FILTERED_DAT" \
        '*/.cache/bazel/*' '*/tests/*' 'tests/*' \
        --output-file "$COVERAGE_FILTERED_DAT"
    # Source dirs are relative to the repo root, passed explicitly because
    # `bazel run` executes in the runfiles tree, not the workspace.
    bazel run "$PKG:add_missing" "$EDITION_FLAG" -- \
        --repo-root "$REPO_PATH" \
        --coverage-file "$COVERAGE_FILTERED_DAT" \
        "${SOURCE_DIRS[@]}"
fi

if [[ "$GENERATE_HTML" == true ]]; then
    if [ ! -f "$COVERAGE_FILTERED_DAT" ]; then
        echo "Error: Coverage data file not found at $COVERAGE_FILTERED_DAT" >&2
        exit 1
    fi
    bazel run @lcov//:genhtml "$EDITION_FLAG" -- \
        --title "Checkmk Unit Test Coverage" \
        --quiet \
        --output "$COVERAGE_HTML_DIR" \
        "$COVERAGE_FILTERED_DAT"
fi

if [[ "$DO_UPLOAD" == true ]]; then
    if [ ! -f "$COVERAGE_FILTERED_DAT" ]; then
        echo "Error: Coverage data file not found at $COVERAGE_FILTERED_DAT" >&2
        exit 1
    fi

    mkdir -p "$COVERAGE_HTML_DIR"
    bazel run "$PKG:summary" "$EDITION_FLAG" -- \
        -i "$COVERAGE_FILTERED_DAT" -o "$RESULT_CSV"
    if [ ! -f "$RESULT_CSV" ]; then
        echo "Error: $RESULT_CSV not created." >&2
        exit 1
    fi

    UPLOAD_ARGS=()
    [[ "$UPLOAD_TOTALS" == true ]] && UPLOAD_ARGS+=(--upload-totals)
    [[ "$UPLOAD_PER_MODULE" == true ]] && UPLOAD_ARGS+=(--upload-per-module)

    echo "Uploading coverage for commit $COMMIT_HASH at $COMMIT_TIME (${UPLOAD_ARGS[*]})"
    bazel run "$PKG:upload" "$EDITION_FLAG" -- \
        --csv-file "$RESULT_CSV" \
        --git-commit-hash "$COMMIT_HASH" \
        --commit-time "$COMMIT_TIME" \
        "${UPLOAD_ARGS[@]}"
fi
