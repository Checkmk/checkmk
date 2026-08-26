#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Definitions shared by the coverage entry points: repository.sh (repository-wide,
# uploads to postgres) and component.sh (one component, local only). What is
# measured and which tests measure it lives here, so a component number stays
# comparable to the dashboard's. Sourced, not executed.

# Every path here is absolute: `bazel run` executes its targets in the runfiles
# tree, not in the workspace, so a relative path handed to one would not resolve.
REPO_PATH="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
# One measurement writes one directory below this one, holding its intermediates,
# its CSV and its HTML.
# shellcheck disable=SC2034  # read by the entry points, not here
RESULTS_ROOT="$REPO_PATH/results/test_coverage"
# Bazel's own combined report, at the one fixed path every coverage run in this
# workspace shares.
COMBINED_DAT="$REPO_PATH/bazel-out/_coverage/_coverage_report.dat"

# Passed to every bazel command that builds something so they share one
# configuration and don't thrash the analysis cache. Omitted for `bazel query`,
# which stops after loading and never analyzes.
EDITION_FLAG="--cmk_edition=ultimate"

# The measured source files, as Bazel labels: what a py rule compiles, minus what
# Bazel marks as test support. `testonly` is enforced -- a non-testonly target may
# not depend on a testonly one -- so a target claiming it has been checked by the
# build, unlike a naming convention. Configuration-less, `bazel query` following
# every select() branch, so one edition's run measures them all.
#
# Filtered to .py: a py rule's srcs also carry the data files beside the code,
# which have no executable line and would otherwise reach the denominator.
source_labels_query() {
    cat <<'EOF'
filter("\.py$", labels(srcs, kind("py_.*", //...) except attr("testonly", 1, //...)))
EOF
}

# The measured source files' labels, or a diagnosis of why there are none.
#
# Both entry points start here, so a query that stopped matching empties every
# selection at once. A failed query is told apart from an empty one, as in
# universe_targets.
source_labels() {
    local query_file=$1 labels
    source_labels_query >"$query_file"
    if ! labels=$(run_target_query "$query_file"); then
        echo "Error: the source file query failed to run; its output is above." >&2
        return 1
    fi
    if [[ -z "$labels" ]]; then
        echo "Error: the source file query matched no file. Check source_labels_query" >&2
        echo "in ${BASH_SOURCE[0]} against a renamed rule kind." >&2
        return 1
    fi
    printf '%s\n' "$labels"
}

# Matches target labels, not file paths, so it constrains what gets instrumented
# but not fully what gets recorded -- see the report filtering in the callers.
#
# Derived from the measured files rather than listed by hand, so the filter cannot
# name a directory the denominator does not, or miss one it does. Top-level only:
# a pattern per Bazel package would be thousands long.
#
# Narrow on purpose. Broadening it to every target pulls some 26k external-repo
# records into the report, and gives the tests whose manifest is empty -- the ones
# coverage.py therefore measures unfiltered -- an include list disjoint from what
# they execute, so they collect nothing and the runner raises NoDataError.
#
# A label in the root package -- //:refresh_compile_commands.py -- names no
# directory, so the grep drops it: an empty alternative would match every label.
# The dot is escaped where the filter is assembled, the filter being a regex:
# .ide would otherwise match aide as well.
instrumentation_filter() {
    local labels_file=$1 filter
    filter=$(sed 's#^//##; s#[/:].*##' "$labels_file" | sort -u | grep -v '^$' | paste -sd'|')
    echo "//(${filter//./\\.})[/:@]"
}

# The measured py_test universe, bound to $t and left open with a trailing `in`
# so the caller appends the expression consuming it.
#
# Selecting by rule kind keeps the non-Python tests' dependencies from being
# built at all -- the Rust agent controller among them, which fails to link
# under coverage instrumentation. Each further exclusion covers a target that
# cannot be measured, or that breaks the run:
#   * doc tests: recognized by their generated runner, since the py_doc_test
#     macro expands to a plain py_test.
#   * requirements tests: py_requirements_test builds its own runner, so nothing
#     starts coverage.py and the target contributes no coverage.dat -- only the
#     cost of building the code it checks under instrumentation, which it takes as
#     data. Matched by tag; Bazel matches attr() against the stringified list, so
#     the bracket/comma delimiters pin the whole tag -- a word boundary would also
#     match a tag like no-requirements.
#   * omd/dependency_management:test_licenses: its SBOM data dep builds the Rust
#     agent controller, which fails to link under instrumentation.
#   * omd/dependency_management:test_manual_dep_manifest: passes under `bazel
#     test` but not under `bazel coverage`, a second coverage.py Collector being
#     created while pytest imports the module, so the runner's cov.stop() finds
#     the wrong one on the stack.
#   * from tests/, only what our test classification calls "package tests":
#     openapi, agent-plugin-unit and unit. Everything else crosses package
#     boundaries.
py_test_universe_query() {
    cat <<'EOF'
let all = kind("py_test", tests(//...)) in
let t = $all
    except attr("srcs", "-doctest-runner\.py", $all)
    except attr("tags", "[\[ ]requirements[,\]]", $all)
    except //omd/dependency_management:test_licenses
    except //omd/dependency_management:test_manual_dep_manifest
    except (//tests/... except (//tests/openapi/... + //tests/agent-plugin-unit/... + //tests/unit/...))
in
EOF
}

# The measured universe's targets, or a diagnosis of why there are none.
#
# Both entry points start from this same query, so an exclusion that stopped
# matching empties every selection at once -- worth saying once, here, rather than
# letting each caller guess. A failed query is told apart from an empty one: a
# caller testing emptiness with `[[ -z "$(...)" ]]` cannot, the command
# substitution sitting in a condition where errexit is suspended and the status
# unobservable.
universe_targets() {
    local query_file=$1 targets
    {
        py_test_universe_query
        # shellcheck disable=SC2016  # $t is bazel query let-syntax, not a shell variable
        echo '$t'
    } >"$query_file"
    if ! targets=$(run_target_query "$query_file"); then
        echo "Error: the py_test universe query failed to run; its output is above." >&2
        return 1
    fi
    if [[ -z "$targets" ]]; then
        echo "Error: the py_test universe query matched no target. Check" >&2
        echo "py_test_universe_query in ${BASH_SOURCE[0]} against a renamed rule kind" >&2
        echo "or an exclusion that stopped matching." >&2
        return 1
    fi
    printf '%s\n' "$targets"
}

# Run a bazel query from a file and keep only target labels: the Aspect CLI
# writes first-run prompt escape sequences to stdout, which would otherwise be
# parsed as target patterns.
#
# Querying into a variable rather than piping, so that an empty result reaches
# the caller to judge -- through a pipe, grep's exit 1 would kill it under
# `set -e` before its own check -- while a query failure stays fatal.
run_target_query() {
    local query_file=$1 output
    output=$(bazel query --query_file="$query_file") || return $?
    grep '^//' <<<"$output" || true
}

# Run `bazel coverage` over a target list, leaving the combined report at
# COMBINED_DAT. That path is removed first, so a run that leaves it unwritten is
# an error here rather than whichever measurement wrote it last.
#
# --test_tag_filters must re-exclude manual tests, which an explicit target list
# would otherwise pull back in.
# --skip_incompatible_explicit_targets: the universe query is configuration-less,
# so it also lists tests incompatible with the edition above, whose mere presence
# on the command line would otherwise fail the build.
#
# Cached test results still contribute their coverage.dat to the combined report,
# so re-running is affordable and measures the same thing.
#
# A failing suite is fatal and reported here rather than by the callers: the
# aspect_rules_py runner writes its lcov report only on a green exit, so a
# failing test leaves an empty coverage.dat behind and the lines only it reaches
# read as uncovered -- a number quietly too low rather than a missing one.
# Returns bazel's own exit status, so a caller can tell a build failure from a
# failing test; 1 if the run produced no report at all.
run_coverage() {
    local target_file=$1 log=$2 labels_file=$3

    local status

    # Not covered by the callers' `set -e`: they invoke this function as
    # `run_coverage ... || exit 1`, and errexit is suspended for the whole body of
    # a function whose status is being tested.
    rm -f "$COMBINED_DAT" || return 1
    bazel coverage --target_pattern_file="$target_file" \
        "$EDITION_FLAG" \
        --skip_incompatible_explicit_targets \
        --test_tag_filters=-manual \
        --keep_going \
        --build_tests_only \
        --combined_report=lcov \
        --instrumentation_filter="$(instrumentation_filter "$labels_file")" \
        2>&1 | tee "$log"
    status=${PIPESTATUS[0]}
    if ((status != 0)); then
        echo "Error: the coverage run did not succeed, so no report is written -- what" >&2
        echo "a suite covers is only meaningful once it passes. Fix the failures and run" >&2
        echo "this again; cached results make the second run cheap. Full output:" >&2
        echo "  $log" >&2
        return "$status"
    fi
    if [[ ! -f "$COMBINED_DAT" ]]; then
        echo "Error: the coverage run wrote no combined report at $COMBINED_DAT," >&2
        echo "so nothing was measured. Did every selected target get skipped?" >&2
        return 1
    fi
}

# Render an lcov tracefile to HTML. Compass derives each module's report link
# from genhtml's default naming (<module path>.gcov.html), so --flat,
# --hierarchical or --html-extension would break every dashboard link.
#
# --run_under: the source paths are workspace-relative, but `bazel run` executes
# genhtml in an empty runfiles dir where they do not resolve.
#
# --ignore-errors downgrades two strictness checks that are real properties of
# the source rather than corrupt data: `inconsistent` for a closure defined in
# both branches of an if/else, `category` for the lines genhtml cannot classify.
generate_html() {
    local coverage_dat=$1 output_dir=$2 title=$3

    # genhtml writes one page per source file and never removes stale ones, so a
    # file that left the report keeps its page and its old number at a deep link.
    rm -rf "$output_dir"
    bazel run @lcov//:genhtml "$EDITION_FLAG" --run_under="cd $REPO_PATH &&" -- \
        --ignore-errors inconsistent,category \
        --title "$title" \
        --quiet \
        --output "$output_dir" \
        "$coverage_dat"

    # genhtml's low/medium/high limits (75%/90%) can be moved but not switched
    # off, and no pair of them fits a report spanning the whole product, so
    # recolor all three alike and let the bar graph's fill length carry the rate.
    # Match only the rate classes -- coverFn{,Alias}{Lo,Hi} reuse the Lo/Hi
    # suffixes for a binary hit/miss signal and keep their coloring. The td
    # qualifier matches genhtml's own td.coverPerLo specificity, so appending
    # after it is what makes the override win.
    #
    # Require the stylesheet: appending to a path genhtml did not write leaves an
    # orphan nobody loads, and the coloring comes back with nothing failing.
    #
    # The bar graph is drawn from images, so a filter chain recolors it:
    # contrast(0) flattens all three to one grey, which sepia and hue-rotate tint
    # to roughly genhtml's own #6688d4 (its COLOR_03). snow.png, the unfilled
    # part, stays white. The table background below is its COLOR_06, which
    # genhtml uses for the directory-name cells -- a neutral already in the
    # palette, since every rate class carries a verdict colour.
    if [[ ! -f "$output_dir/gcov.css" ]]; then
        echo "Error: genhtml did not write $output_dir/gcov.css; cannot neutralize" >&2
        echo "the low/medium/high coloring." >&2
        return 1
    fi
    cat >>"$output_dir/gcov.css" <<'EOF'

/* Neutralize the low/medium/high coloring, see common.sh */
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
}
