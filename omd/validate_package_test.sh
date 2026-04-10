#!/bin/bash
# Validates RPATH/RUNPATH correctness in a built DEB, RPM, or CMA package.
# Arguments are supplied by the sh_test rule via $(location ...) expansion:
#   $1  path to the package file (.deb, .rpm, or .cma)
#   $2  path to the package_validator binary
#   $3  path to the ignore-files file
#   $4+ paths to system-dependencies files (one or more, merged by the validator)
set -euo pipefail

PACKAGE="$1"
VALIDATOR="$2"
IGNORE_FILES="$3"
shift 3

# $TEST_UNDECLARED_OUTPUTS_DIR is set by Bazel; everything written here is
# archived automatically into test.outputs/outputs.zip alongside test.log.
REPORT="${TEST_UNDECLARED_OUTPUTS_DIR}/report.json"

ARGS=("$PACKAGE" "$REPORT")
for f in "$@"; do
    ARGS+=(--system-dependencies "$f")
done
ARGS+=(--ignore-files "$IGNORE_FILES")

"$VALIDATOR" "${ARGS[@]}"
