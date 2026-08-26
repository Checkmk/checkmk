#!/bin/bash
#
# Small helper to remove all unused file level mypy suppressions.
# For every suppressions type:
#  * remove all suppressions
#  * run mypy
#  * reset all files for which this causes errros
#  * create a commit for the changed files
#
# Run from repo root.
#
#

set -o pipefail

TMPFILE="$(mktemp)"

run_mypy() {
    echo "Running: bazel build --config=mypy ..."
    bazel build --config=mypy ...
}

list_files_with_suppression() {
    ag "^# mypy: disable-error-code=\"$1\"" -l
}

list_all_used_suppression_types() {
    ag --nofilename -o '(?<=^# mypy: disable-error-code=")[^"]*' | sort | uniq
}

extract_failed_files() {
    # cp "${1}" "${1}.${2}.failed"  # for debugging
    grep ": error:" "${1}" | cut -d: -f1 | uniq
}

remove_suppression() {
    st="$1"
    # remove all suppressions
    echo "Removing '# mypy: disable-error-code=\"${st}\"'"
    # shellcheck disable=SC2046  # we want word splitting here
    sed -i "/# mypy: disable-error-code=\"${st}\"/d" $(list_files_with_suppression "${st}")
    echo "Changed files: $(git df | wc -l)"

    # Run linters and restore failures
    while ! run_mypy 2>&1 | tee "${TMPFILE}"; do
        echo "Checking failing files back out"
        # check them out individually, to avoid looping forever upon files unknown to git (like bazel artifacts)
        for f in $(extract_failed_files "${TMPFILE}" "${st}"); do
            git checkout "${f}"
        done
        echo "Changed files: $(git df | wc -l)"
    done
    # we're removing lines before the imports. This is 'reformatting':
    bazel lint --fix //...
    git commit -am "Remove unnecessary mypy suppression: ${st}"
}

main() {
    echo "Removing unused mypy suppressions. This will take a while."
    for st in $(list_all_used_suppression_types); do
        echo "====================== ${st} =========================="
        remove_suppression "${st}"
    done
    rm -f "${TMPFILE}"
}

main
