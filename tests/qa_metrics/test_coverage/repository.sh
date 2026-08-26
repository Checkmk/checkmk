#!/usr/bin/env bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=tests/qa_metrics/test_coverage/common.sh
source "$SCRIPT_DIR/common.sh"

# Operate from the repo root for the rest of the script: the git metadata
# queries below and bazel (which locates the workspace from the working
# directory) all need to run inside the workspace.
cd "$REPO_PATH"

# Every tool is invoked through `bazel run` so Bazel provides it hermetically --
# no venv activation, no PATH manipulation.
PKG="//tests/qa_metrics/test_coverage"

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

RESULT_DIR="$RESULTS_ROOT/repository"
PY_TEST_TARGETS="$RESULT_DIR/py_test_targets.txt"
QUERY_FILE="$RESULT_DIR/py_test_universe_query.txt"
SOURCE_LABELS_QUERY="$RESULT_DIR/source_labels_query.txt"
SOURCE_LABELS="$RESULT_DIR/source_labels.txt"
COVERAGE_LOG="$RESULT_DIR/coverage.log"
SCOPED_DAT="$RESULT_DIR/scoped.dat"
SOURCE_PATHS="$RESULT_DIR/source_paths.txt"
COVERAGE_HTML_DIR="$RESULT_DIR/html"
RESULT_CSV="$RESULT_DIR/coverage.csv"

mkdir -p "$RESULT_DIR"

if [[ "$RUN" == true ]]; then
    # The universe is used unrestricted: every test in it contributes to the
    # repository-wide number. Passed via --target_pattern_file, the list being
    # too long for the command line.
    universe_targets "$QUERY_FILE" >"$PY_TEST_TARGETS"

    # Which files are measured. Needed before the run, the instrumentation filter
    # being derived from them.
    source_labels "$SOURCE_LABELS_QUERY" >"$SOURCE_LABELS" || exit 1

    # Every test in the universe contributes, and the run must be green: a
    # number from a suite that did not pass says nothing about what it covers.
    run_coverage "$PY_TEST_TARGETS" "$COVERAGE_LOG" "$SOURCE_LABELS" || exit 1

    # The files the number is about. Enumerated once and used twice below, so
    # the records that survive and the files counted at 0% are the same set.
    bazel run "$PKG:source_files" "$EDITION_FLAG" -- \
        --repo-root "$REPO_PATH" \
        --source-labels "$SOURCE_LABELS" \
        --paths-out "$SOURCE_PATHS"
    bazel run "$PKG:scope" "$EDITION_FLAG" -- \
        --repo-root "$REPO_PATH" \
        --coverage-file "$COMBINED_DAT" \
        --file-list "$SOURCE_PATHS" \
        --output "$SCOPED_DAT"
fi

if [[ "$GENERATE_HTML" == true ]]; then
    if [ ! -f "$SCOPED_DAT" ]; then
        echo "Error: Coverage data file not found at $SCOPED_DAT" >&2
        exit 1
    fi
    generate_html "$SCOPED_DAT" "$COVERAGE_HTML_DIR" \
        "Checkmk Test Coverage"
fi

if [[ "$DO_UPLOAD" == true ]]; then
    if [ ! -f "$SCOPED_DAT" ]; then
        echo "Error: Coverage data file not found at $SCOPED_DAT" >&2
        exit 1
    fi

    bazel run "$PKG:summary" "$EDITION_FLAG" -- \
        -i "$SCOPED_DAT" -o "$RESULT_CSV"
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
