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
# bazel command that builds something (`bazel coverage` and `bazel run`) so they
# all share one build configuration and don't thrash the analysis cache. It is
# omitted for `bazel query`, which stops after the loading phase and never
# analyzes.
EDITION_FLAG="--cmk_edition=ultimate"
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

# File arguments are absolute, since `bazel run` executes its targets in the
# runfiles tree, not in this directory. This measurement writes one directory,
# holding its intermediates, its CSV and its HTML.
# Bazel's own, at the one fixed path every coverage run in this workspace shares.
COMBINED_DAT="$REPO_PATH/bazel-out/_coverage/_coverage_report.dat"
RESULT_DIR="$REPO_PATH/results/test_coverage/repository"
PY_TEST_TARGETS="$RESULT_DIR/py_test_targets.txt"
COVERAGE_FILTERED_DAT="$RESULT_DIR/filtered.dat"
COVERAGE_HTML_DIR="$RESULT_DIR/html"
RESULT_CSV="$RESULT_DIR/coverage.csv"

mkdir -p "$RESULT_DIR"

if [[ "$RUN" == true ]]; then
    filter=$(
        IFS='|'
        echo "${SOURCE_DIRS[*]}"
    )

    # Restrict coverage to Python tests. Selecting by rule kind (py_test) drops
    # rust_test/cc_test/js_test/shell tests and the deploy drift test, so their
    # non-Python dependencies -- e.g. the Rust agent controller, which fails to
    # link under coverage instrumentation -- are never built. On top of that:
    #   * doc tests are dropped; the py_doc_test macro expands to a plain
    #     py_test, so they are recognized by their generated runner script
    #   * tests/unit/qa_metrics is dropped: it tests the QA tooling under
    #     tests/qa_metrics, which is not part of the source code whose coverage
    #     we measure, so running it under coverage contributes nothing. For
    #     change_quality it would even fail the run: its instrumented
    #     dependencies (cmk-ccc, cmk-werks, pulled in transitively via the
    #     untested push.py) are never imported by its tests, so coverage.py
    #     collects no data and the aspect_rules_py test runner crashes with
    #     NoDataError, failing a target whose tests all pass.
    #   * omd is dropped: its py_tests cover license/BOM tooling, not shipped
    #     source code. test_licenses would even fail the run: its
    #     list_of_dependencies data dep generates an SBOM of the whole product
    #     payload, so building the test's runfiles builds the Rust agent
    #     controller -- coverage-instrumented, since //packages matches the
    #     instrumentation filter -- and that link fails (undefined gcov
    #     references in the static musl link).
    #   * From tests/, only keep openapi, agent-plugin-unit, unit. In particular,
    #     we don't want integration or system tests. They are currently anyway not
    #     bazelized, but even if they were, we wouldn't want to include them in
    #     our coverage measurements. We only want include what we classify as
    #     "Package tests" in our test classification. All other tests cross
    #     package / component boundaries and shouldn't be included when measuring
    #     the coverage. The same holds for eg. tests/plugins_consistency.
    # The list is passed via --target_pattern_file since it is too long for
    # the command line.
    # Querying into a variable rather than piping: an empty result has to reach
    # the check below, and through a pipe grep's exit 1 would kill the script
    # under `set -e` before it. Only target labels are kept, since the Aspect CLI
    # writes first-run prompt escape sequences to stdout.
    # shellcheck disable=SC2016  # $t is bazel query let-syntax, not a shell variable
    universe=$(bazel query '
        let t = kind("py_test", tests(//...)) in
        $t
        except attr("srcs", "-doctest-runner\.py", $t)
        except //tests/unit/qa_metrics/...
        except //omd/...
        except (//tests/... except (//tests/openapi/... + //tests/agent-plugin-unit/... + //tests/unit/...))
    ')
    universe=$(grep '^//' <<<"$universe" || true)
    if [[ -z "$universe" ]]; then
        echo "Error: the py_test universe query matched no target. Check the query" >&2
        echo "above against a renamed rule kind or an exclusion that stopped matching." >&2
        exit 1
    fi
    printf '%s\n' "$universe" >"$PY_TEST_TARGETS"

    # --test_tag_filters must re-exclude manual tests: they are excluded from
    # wildcard builds for a reason (e.g. benchmarks), but the explicit target
    # list from the query above would override the manual tag.
    # --skip_incompatible_explicit_targets: the query is configuration-less, so
    # it also lists edition-gated tests (e.g. //cmk:requirements-test-community)
    # that are platform-incompatible under the edition set above. Without the
    # flag their mere presence on the command line fails the build ("not all
    # targets were analyzed") even when every executed test passes.
    #
    # The combined report is removed first so a run that leaves it unwritten is
    # an error here, rather than letting the steps below read whichever
    # measurement wrote it last.
    rm -f "$COMBINED_DAT"
    bazel coverage --target_pattern_file="$PY_TEST_TARGETS" \
        "$EDITION_FLAG" \
        --skip_incompatible_explicit_targets \
        --test_tag_filters=-manual \
        --keep_going \
        --build_tests_only \
        --combined_report=lcov \
        --instrumentation_filter="//(${filter})[/:@]"
    if [ ! -f "$COMBINED_DAT" ]; then
        echo "Error: the coverage run wrote no combined report at $COMBINED_DAT," >&2
        echo "so nothing was measured. Did every selected target get skipped?" >&2
        exit 1
    fi
    # Strip the repo root prefix so paths are workspace-relative
    sed -i "s|^SF:${REPO_PATH}/|SF:|g" "$COMBINED_DAT"
    # Filter the report down to our own source code. This is needed because the
    # instrumentation filter above does not fully constrain what gets recorded:
    # for a test whose dependencies all lie outside the instrumented dirs (e.g.
    # //scripts:requirements-test), Bazel hands the test an empty
    # COVERAGE_MANIFEST, aspect_rules_py passes the manifest to coverage.py as
    # its `include` list, and an empty include list means "no filter" --
    # coverage.py then records everything the test executes: its own sources,
    # pip packages from the bazel cache, the pytest runner itself.
    bazel run @lcov//:lcov "$EDITION_FLAG" -- \
        --extract "$COMBINED_DAT" \
        "${SOURCE_DIRS[@]/%//*.py}" \
        --output-file "$COVERAGE_FILTERED_DAT"
    # lcov matches patterns as unanchored substrings, so the --extract above
    # also keeps leaked pip files ('packages/*.py' matches their
    # site-packages/... paths). Remove what slipped through:
    #   '*/.cache/bazel/*': leaked pip packages that survived --extract
    #   '*/tests/*':        test helpers nested inside source dirs
    #                       (e.g. non-free/tests/testlib)
    #   'tests/*':          defensive, matches nothing in normal runs: a leaked
    #                       top-level test source whose path contains a source
    #                       dir as substring (e.g. tests/unit/cmk/...) would
    #                       survive --extract yet dodge '*/tests/*'
    # --ignore-errors unused: lcov 2.x aborts when a pattern matches nothing,
    # but 'tests/*' being unused is the expected steady state.
    bazel run @lcov//:lcov "$EDITION_FLAG" -- \
        --remove "$COVERAGE_FILTERED_DAT" \
        '*/.cache/bazel/*' '*/tests/*' 'tests/*' \
        --ignore-errors unused \
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
    # The coverage data stores source paths workspace-relative, but `bazel run`
    # executes genhtml in an (empty) runfiles dir, so it cannot find the sources.
    # --run_under changes into the repo root so the relative paths resolve.
    #
    # --ignore-errors downgrades two benign genhtml strictness checks:
    #   inconsistent: a closure defined in mutually exclusive if/else branches
    #     yields one qualified function name with two start lines, e.g. both
    #     inner defs below are f.<locals>.g but start on different lines:
    #         def f(cond):
    #             if cond:
    #                 def g(): ...
    #             else:
    #                 def g(): ...
    #   category: genhtml fails to classify a few lines (reports category 'UNK').
    # Both are real properties of the source, not corrupt data.
    # genhtml writes one page per source file and never removes stale ones, so a
    # file that left the report keeps its page and its old number at a deep link.
    rm -rf "$COVERAGE_HTML_DIR"
    bazel run @lcov//:genhtml "$EDITION_FLAG" --run_under="cd $REPO_PATH &&" -- \
        --ignore-errors inconsistent,category \
        --title "Checkmk Test Coverage" \
        --quiet \
        --output "$COVERAGE_HTML_DIR" \
        "$COVERAGE_FILTERED_DAT"

    # genhtml's low/medium/high limits (75%/90%) can be moved but not switched
    # off, and no pair of them fits a report spanning the whole product, so
    # recolor all three alike and let the bar graph's fill length carry the rate.
    # Only the rate classes: coverFn{,Alias}{Lo,Hi} and the source view's
    # tlaGNC/tlaUNC reuse the suffixes for a binary hit/miss signal. The td
    # qualifier beats genhtml's own td.coverPerLo on specificity.
    #
    # Require the stylesheet: appending to a path genhtml did not write leaves an
    # orphan nobody loads, and the coloring back with nothing failing.
    #
    # The bar graph is drawn from images, so a filter chain recolors it:
    # contrast(0) flattens all three to one grey, which sepia and hue-rotate tint
    # to roughly genhtml's own #6688d4. snow.png, the unfilled part, stays white.
    if [[ ! -f "$COVERAGE_HTML_DIR/gcov.css" ]]; then
        echo "Error: genhtml wrote no $COVERAGE_HTML_DIR/gcov.css, so the low/medium/high" >&2
        echo "coloring cannot be neutralized." >&2
        exit 1
    fi
    cat >>"$COVERAGE_HTML_DIR/gcov.css" <<'EOF'

/* Neutralize the low/medium/high coloring, see main.sh */
td[class$="coverPerLo"], td[class$="coverPerMed"], td[class$="coverPerHi"],
td[class$="coverNumLo"], td[class$="coverNumMed"], td[class$="coverNumHi"],
td.headerCovTableEntryLo, td.headerCovTableEntryMed, td.headerCovTableEntryHi
{
  background-color: #b8d0ff;
}

td.coverBarOutline img:not([src$="snow.png"])
{
  filter: contrast(0) sepia(1) hue-rotate(192deg) saturate(4) brightness(0.85);
}
EOF
fi

if [[ "$DO_UPLOAD" == true ]]; then
    if [ ! -f "$COVERAGE_FILTERED_DAT" ]; then
        echo "Error: Coverage data file not found at $COVERAGE_FILTERED_DAT" >&2
        exit 1
    fi

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
