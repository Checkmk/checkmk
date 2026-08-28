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
SOURCE_LABELS_QUERY="$RESULT_DIR/source_labels_query.txt"
SOURCE_LABELS="$RESULT_DIR/source_labels.txt"
SCOPED_DAT="$RESULT_DIR/scoped.dat"
SOURCE_PATHS="$RESULT_DIR/source_paths.txt"
COVERAGE_HTML_DIR="$RESULT_DIR/html"
RESULT_CSV="$RESULT_DIR/coverage.csv"

mkdir -p "$RESULT_DIR"

if [[ "$RUN" == true ]]; then
    # The measured source files, as Bazel labels: what a py rule compiles, minus
    # what Bazel marks as test support. `testonly` is enforced -- a non-testonly
    # target may not depend on a testonly one -- so a target claiming it has been
    # checked by the build, unlike a naming convention. Configuration-less, the
    # query following every select() branch, so one edition's run measures them
    # all.
    #
    # Filtered to .py: a py rule's srcs also carry the data files beside the code,
    # which have no executable line and would otherwise reach the denominator.
    #
    # Read into a variable and label-filtered for the same reasons as the universe
    # query below.
    cat >"$SOURCE_LABELS_QUERY" <<'EOF'
filter("\.py$", labels(srcs, kind("py_.*", //...) except attr("testonly", 1, //...)))
EOF
    labels=$(bazel query --query_file="$SOURCE_LABELS_QUERY")
    labels=$(grep '^//' <<<"$labels" || true)
    if [[ -z "$labels" ]]; then
        echo "Error: the source file query matched no file. Check the query above" >&2
        echo "against a renamed rule kind." >&2
        exit 1
    fi
    printf '%s\n' "$labels" >"$SOURCE_LABELS"

    # Derived from the measured files rather than listed by hand, so the filter
    # cannot name a directory the denominator does not, or miss one it does.
    # Top-level only: a pattern per Bazel package would be thousands long.
    #
    # Narrow on purpose. Broadening it to every target pulls some 26k
    # external-repo records into the report, and gives the tests whose manifest
    # is empty -- the ones coverage.py therefore measures unfiltered -- an
    # include list disjoint from what they execute, so they collect nothing and
    # the runner raises NoDataError.
    #
    # A label in the root package -- //:refresh_compile_commands.py -- names no
    # directory, so the grep drops it: an empty alternative would match every
    # label. The dot is escaped where the filter is assembled, the filter being a
    # regex: .ide would otherwise match aide as well.
    filter=$(sed 's#^//##; s#[/:].*##' "$SOURCE_LABELS" | sort -u | grep -v '^$' | paste -sd'|')

    # Restrict coverage to Python tests. Selecting by rule kind (py_test) drops
    # rust_test/cc_test/js_test/shell tests and the deploy drift test, so their
    # non-Python dependencies -- e.g. the Rust agent controller, which fails to
    # link under coverage instrumentation -- are never built. On top of that:
    #   * doc tests are dropped; the py_doc_test macro expands to a plain
    #     py_test, so they are recognized by their generated runner script
    #   * requirements tests are dropped: py_requirements_test builds its own
    #     runner, so nothing starts coverage.py and the target contributes no
    #     coverage.dat -- only the cost of building the code it checks under
    #     instrumentation, which it takes as data. Matched by tag; Bazel matches
    #     attr() against the stringified list, so the bracket/comma delimiters
    #     pin the whole tag -- a word boundary would also match a tag like
    #     no-requirements.
    #   * omd/dependency_management:test_licenses is dropped: its
    #     list_of_dependencies data dep generates an SBOM of the whole product
    #     payload, so building the test's runfiles builds the Rust agent
    #     controller -- coverage-instrumented -- and that link fails (undefined
    #     gcov references in the static musl link).
    #   * omd/dependency_management:test_manual_dep_manifest is dropped: it
    #     passes under `bazel test` but not under `bazel coverage`, a second
    #     coverage.py Collector being created while pytest imports the module, so
    #     the runner's cov.stop() finds the wrong one on the stack.
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
        except attr("tags", "[\[ ]requirements[,\]]", $t)
        except //omd/dependency_management:test_licenses
        except //omd/dependency_management:test_manual_dep_manifest
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
        --instrumentation_filter="//(${filter//./\\.})[/:@]"
    if [ ! -f "$COMBINED_DAT" ]; then
        echo "Error: the coverage run wrote no combined report at $COMBINED_DAT," >&2
        echo "so nothing was measured. Did every selected target get skipped?" >&2
        exit 1
    fi

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
        "$SCOPED_DAT"

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
