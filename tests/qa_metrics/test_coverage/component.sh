#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Python test coverage of a single component, measured locally.
#
# Has no upload path: a number from a partial suite must never reach the history
# table, and separate entry points make that structural. Differs from the nightly
# in which tests are run and which files stay in the report, nothing else.
#
# Known limitations, all of which can make the number differ from the dashboard:
#   * Ownership comes from the OWNERS files on Gerrit's master, so a source file
#     added on a feature branch does not count until merged.
#   * Selection follows Bazel's graph, so dynamically loaded code is invisible.
#   * A test is selected for depending on the component's code, not for belonging
#     to it, so lines only a dependent's test reaches count as covered.
#   * A co-owned file counts in full for each owner, so per-component numbers do
#     not add up to the repository total. Compass applies the same rule.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=tests/qa_metrics/test_coverage/common.sh
source "$SCRIPT_DIR/common.sh"

# Operate from the repo root: the git queries below and bazel (which locates the
# workspace from the working directory) all need to run inside the workspace.
cd "$REPO_PATH"

PKG="//tests/qa_metrics/test_coverage"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

COMPONENT=""

usage() {
    cat <<EOF
Usage: $0 <component-id>

  <component-id>   Component to measure, as named in the OWNERS files
                   (a directory name below component_owners/).

Runs every test that depends on the component's code and reports coverage of the
source files the component owns.

The number can differ from the dashboard's, all for documented reasons: ownership
comes from Gerrit's master, selection follows Bazel's graph and so misses
dynamically loaded code, a test counts for depending on the component's code
rather than for belonging to it, and a co-owned file counts in full for each
owner. See the comment at the top of this script.

Writes results/test_coverage/components/<component-id>/:
  coverage.csv    per-file numbers
  html/           HTML report
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help | -h)
            usage
            exit 0
            ;;
        -*)
            echo "Error: Unknown argument '$1'" >&2
            echo "Run '$0 --help' for usage." >&2
            exit 1
            ;;
        *)
            if [[ -n "$COMPONENT" ]]; then
                echo "Error: measure one component at a time (got '$COMPONENT' and '$1')" >&2
                exit 1
            fi
            COMPONENT="$1"
            shift
            ;;
    esac
done

if [[ -z "$COMPONENT" ]]; then
    echo "Error: no component given." >&2
    usage >&2
    exit 1
fi

# Component ids hold only [a-z0-9_]; rejecting anything else keeps the id safe to
# paste into the output paths below.
if [[ ! "$COMPONENT" =~ ^[a-z0-9_]+$ ]]; then
    echo "Error: '$COMPONENT' is not a valid component id ([a-z0-9_])." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------

RESULT_DIR="$RESULTS_ROOT/components/$COMPONENT"
OWNED_PATHS="$RESULT_DIR/owned_paths.txt"
OWNED_PACKAGES="$RESULT_DIR/owned_packages.txt"
SOURCE_LABELS_QUERY="$RESULT_DIR/source_labels_query.txt"
SOURCE_LABELS="$RESULT_DIR/source_labels.txt"
SELECTION_QUERY="$RESULT_DIR/selection_query.txt"
UNIVERSE_QUERY="$RESULT_DIR/universe_query.txt"
SELECTED_TARGETS="$RESULT_DIR/selected_targets.txt"
COVERAGE_LOG="$RESULT_DIR/coverage.log"
COMPONENT_DAT="$RESULT_DIR/scoped.dat"
RESULT_CSV="$RESULT_DIR/coverage.csv"
TOTAL_CSV="$RESULT_DIR/total.csv"
COVERAGE_HTML_DIR="$RESULT_DIR/html"

mkdir -p "$RESULT_DIR"

# 1. Which files are measured at all? The same list the nightly uses, so a
#    component's number stays comparable to the dashboard's.
source_labels "$SOURCE_LABELS_QUERY" >"$SOURCE_LABELS" || exit 1

# 2. Which of them does the component own, and which Bazel packages hold them?
#    Test support is already out: tests are selected by dependency, not ownership.
bazel run "$PKG:owned_files" "$EDITION_FLAG" -- \
    --component "$COMPONENT" \
    --repo-root "$REPO_PATH" \
    --source-labels "$SOURCE_LABELS" \
    --paths-out "$OWNED_PATHS" \
    --packages-out "$OWNED_PACKAGES"

# 3. Which tests to run? Every test that can cover the component. The intersect
#    is what matters: rdeps alone also returns the py_library hops between a
#    source file and its tests. Patterns are quoted and collected with set(),
#    bazel query reading unquoted words from a limited character set.
if [[ ! -s "$OWNED_PACKAGES" ]]; then
    echo "Error: none of the source files $COMPONENT owns lies in a Bazel package," >&2
    echo "so no test can be selected by dependency on them (examples above). Add" >&2
    echo "BUILD files covering that code to make it measurable." >&2
    exit 1
fi
packages_set=$(sed 's|^|"|; s|$|"|' "$OWNED_PACKAGES" | paste -sd' ')
{
    py_test_universe_query
    # $t is bazel query let-syntax, not a shell variable, hence the escapes.
    echo "\$t intersect rdeps(\$t, set($packages_set))"
} >"$SELECTION_QUERY"
run_target_query "$SELECTION_QUERY" >"$SELECTED_TARGETS"

selected=$(wc -l <"$SELECTED_TARGETS")
if [[ "$selected" -eq 0 ]]; then
    # The universe is shared with the nightly, so an exclusion that stopped
    # matching empties the selection for every component. Ask about it on its own
    # rather than blaming the component for a broken query; universe_targets
    # explains an empty or failed universe itself.
    universe_targets "$UNIVERSE_QUERY" >/dev/null
    echo "Error: no test depending on $COMPONENT's code was found in the measured" >&2
    echo "universe. Nothing would be measured, so there is no coverage number to" >&2
    echo "report." >&2
    exit 1
fi
echo "Selected $selected test target(s) depending on $COMPONENT's code"

# 4. Measure. How the run is configured lives in common.sh, so a component
#    number cannot be measured differently from the dashboard's.
run_coverage "$SELECTED_TARGETS" "$COVERAGE_LOG" "$SOURCE_LABELS" || exit 1

# 5. Scope the tracefile to the component, by the same step and the same kind of
#    list the repository-wide run uses.
bazel run "$PKG:scope" "$EDITION_FLAG" -- \
    --repo-root "$REPO_PATH" \
    --coverage-file "$COMBINED_DAT" \
    --file-list "$OWNED_PATHS" \
    --output "$COMPONENT_DAT"

# 6. Per-file numbers, and the total over them. Two runs over one tracefile,
#    since totalling the CSV here would duplicate summary's aggregation.
bazel run "$PKG:summary" "$EDITION_FLAG" -- \
    -i "$COMPONENT_DAT" -o "$RESULT_CSV"
bazel run "$PKG:summary" "$EDITION_FLAG" -- \
    -i "$COMPONENT_DAT" -o "$TOTAL_CSV" --total-only

generate_html "$COMPONENT_DAT" "$COVERAGE_HTML_DIR" \
    "Checkmk Test Coverage: $COMPONENT"

# 'selected' and 'executed' differ legitimately, since
# --skip_incompatible_explicit_targets drops edition-incompatible targets.
echo
echo "--- $COMPONENT"
echo "Source files owned:    $(wc -l <"$OWNED_PATHS")"
echo "Targets selected:      $selected"
grep -E "^Executed [0-9]+ out of" "$COVERAGE_LOG" | tail -1 || true
echo "Cached results:        $(grep -cE '\(cached\) PASSED' "$COVERAGE_LOG" || true)"
echo "Per-file numbers:      $RESULT_CSV"
echo "Result dir:            $RESULT_DIR"
echo "HTML report:           $COVERAGE_HTML_DIR/index.html"
# Columns are addressed by name, so a reordered CSV cannot print the wrong number.
awk -F, 'NR == 1 { for (i = 1; i <= NF; i++) column[$i] = i; next }
    {
        printf "Line coverage:         %d/%d = %s%%\n",
            $column["covered_lines"], $column["total_lines"],
            $column["lines_coverage_percent"]
    }' "$TOTAL_CSV"
