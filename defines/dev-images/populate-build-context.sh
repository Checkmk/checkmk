#!/usr/bin/env bash
# Note: This should not be necessaray: in order to make files required to build
#       images we need to copy them to the build context we want to use.
#       Moving those files to a dedicated folder (e.g. `defines/`) would make
#       this step obsolete.

set -e

REPO_ROOT="$(cd "$(dirname "$(dirname "$(dirname "${BASH_SOURCE[0]}")")")" >/dev/null 2>&1 && pwd)"

cp \
    "${REPO_ROOT}/defines.make" \
    "${REPO_ROOT}/static_variables.bzl" \
    "${REPO_ROOT}/package_versions.bzl" \
    "${REPO_ROOT}/.bazelversion" \
    "${REPO_ROOT}/omd/strip_binaries" \
    "${1:-.}"
