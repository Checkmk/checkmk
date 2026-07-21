#!/usr/bin/env bash
# Verifies py_requirements_test (bazel/rules:py_requirements_test.bzl) coverage:
#   1. every requirements.in has a py_requirements_test target
#   2. every non-test py_library shipped in the package's own wheel, and every
#      non-test py_binary, is scanned by that package's own py_requirements_test

set -u

fail=0

stderr_file=$(mktemp)
trap 'rm -f "${stderr_file}"' EXIT

# Git-tracked requirements.in files; misses build-time-assembled ones (e.g.
# packages/cmk-plugins), so this alone can't confirm coverage.
existing=$(git ls-files | grep -E '(^|/)requirements\.in$' | sort -u)

# requirements_in attribute of every wired-up py_requirements_test, read
# directly instead of via a full transitive-dependency expansion. Also
# catches build-time-assembled requirements.in files.
governed_query_output=$(bazel query 'labels(requirements_in, kind("_gen_runner", //...))' 2>"${stderr_file}")
governed_rc=$?
if [ "${governed_rc}" -ne 0 ]; then
    echo "bazel query failed (exit ${governed_rc}) while discovering py_requirements_test targets:"
    cat "${stderr_file}"
    exit 1
fi
governed=$(echo "${governed_query_output}" | sed -E 's|^//||; s|:|/|' | sort -u)

# --- every requirements.in has a py_requirements_test -----------------------

missing_targets=$(comm -23 <(echo "${existing}") <(echo "${governed}"))

if [ -n "${missing_targets}" ]; then
    echo "Found \"requirements.in\" files without a py_requirements_test target:"
    echo "${missing_targets}"
    fail=1
fi

current=$(printf '%s\n%s\n' "${existing}" "${governed}" | grep -v '^$' | sort -u)

# --- every non-test py_library/py_binary is scanned by its own package's ---
# --- py_requirements_test ----------------------------------------------------
#
# Libraries are anchored on "ships in the wheel", since that's the only
# contract requirements.in governs for them; a package with no
# requires=[]-less wheel (e.g. cmk, scripts) has no candidates and passes
# vacuously. Binaries can't ship in a wheel, so every py_binary in the
# package is a candidate regardless.
missing_libs_query=""
while IFS= read -r f; do
    [ -z "${f}" ] && continue
    # Already flagged as missing a py_requirements_test entirely by check 1.
    if echo "${missing_targets}" | grep -qxF "${f}"; then
        continue
    fi

    pkg_root="//$(dirname "${f}"):*"
    pkg_scope="//$(dirname "${f}")/..."
    gen_runner="kind(\"_gen_runner\", ${pkg_root})"
    governed_wheels="kind(\"py_wheel rule\", ${pkg_root}) intersect attr(requires, \"^\\[\\]\$\", ${pkg_root})"
    governed_libs="kind(\"py_library rule\", ${pkg_scope}) intersect deps(${governed_wheels})"
    binaries="kind(\"py_binary rule\", ${pkg_scope})"

    missing_libs_query+="${missing_libs_query:++}"
    missing_libs_query+="((${governed_libs} union ${binaries})"
    missing_libs_query+=" except attr(testonly, 1, ${pkg_scope})"
    missing_libs_query+=" except deps(${gen_runner}))"
done <<<"${current}"

if [ -n "${missing_libs_query}" ]; then
    query_output=$(bazel query "${missing_libs_query}" 2>"${stderr_file}")
    query_rc=$?
    if [ "${query_rc}" -ne 0 ]; then
        echo "bazel query failed (exit ${query_rc}) while checking py_library/py_binary coverage:"
        cat "${stderr_file}"
        exit 1
    fi
    missing_libs=$(echo "${query_output}" | sort)
    if [ -n "${missing_libs}" ]; then
        echo "Found py_library/py_binary targets not covered by their own package's py_requirements_test (add them to its libs):"
        echo "${missing_libs}"
        fail=1
    fi
fi

exit ${fail}
