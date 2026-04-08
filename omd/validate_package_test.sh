#!/bin/bash
# Validates RPATH/RUNPATH correctness in a built DEB or RPM package.
# Arguments are supplied by the sh_test rule via $(location ...) expansion:
#   $1  path to the package file (.deb or .rpm)
#   $2  path to the package_validator binary
#   $3  path to the system-dependencies file
#   $4  path to the ignore-files file (optional)
set -euo pipefail

PACKAGE="$1"
VALIDATOR="$2"
SYSTEM_DEPS="$3"
IGNORE_FILES="${4:-}"

# $TEST_UNDECLARED_OUTPUTS_DIR is set by Bazel; everything written here is
# archived automatically into test.outputs/outputs.zip alongside test.log.
REPORT="${TEST_UNDECLARED_OUTPUTS_DIR}/report.json"

ARGS=("$PACKAGE" "$REPORT" --system-dependencies "$SYSTEM_DEPS")
if [[ -n "$IGNORE_FILES" ]]; then
    ARGS+=(--ignore-files "$IGNORE_FILES")
fi

"$VALIDATOR" "${ARGS[@]}"
