#!/usr/bin/env bash
# Verify every package_docs target is listed in //doc/documentation:srcs.
#
# Bazel cannot collect targets by rule kind during a build, so the list in
# doc/documentation/BUILD is maintained by hand. A package_docs target missing
# from it builds fine, but its pages never reach the documentation.
#
# `bazel query` follows all branches of a select(), so entries that are only
# listed for some editions count as listed.

set -eu -o pipefail

main() {
    local missing
    if ! missing=$(bazel query --output=label \
        'kind("^package_docs rule$", //...) except deps(//doc/documentation:srcs, 1)'); then
        echo "ERROR: bazel query for package_docs targets failed" >&2
        return 1
    fi
    [[ -z "${missing}" ]] && return 0
    echo "ERROR: package_docs targets missing from //doc/documentation:srcs in doc/documentation/BUILD:" >&2
    echo "${missing}" >&2
    return 1
}

main "$@"
