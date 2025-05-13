#!/usr/bin/env bash
# Note: This should not be necessaray: in order to make files required to build
#       images we need to copy them to the build context we want to use.
#       Moving those files to a dedicated folder (e.g. `defines/`) would make
#       this step obsolete.

set -e

REPO_ROOT="$(cd "$(dirname "$(dirname "$(dirname "${BASH_SOURCE[0]}")")")" >/dev/null 2>&1 && pwd)"
TARGET_DIR="$(realpath "${1:-.}")"

(
    cd "${REPO_ROOT}/buildscripts/infrastructure/build-nodes/scripts"
    cp \
        build_lib.sh \
        Check_MK-pubkey.gpg \
        install-iwyu.sh install-clang.sh \
        install-docker.sh \
        install-nodejs.sh \
        install-packer.sh \
        install-make-dist-deps.sh \
        install-aws-cli.sh \
        install-bazel.sh \
        install-cmake.sh \
        install-cmk-dependencies.sh \
        install-gdb.sh \
        install-gnu-toolchain.sh \
        install-openssl.sh \
        install-patchelf.sh \
        install-protobuf-cpp.sh \
        install-python.sh \
        install-rust-cargo.sh \
        install-valgrind.sh \
        ci.bazelrc \
        "${TARGET_DIR}"
)

cp \
    "${REPO_ROOT}/omd/distros/"*.mk \
    "${TARGET_DIR}"

cp \
    "${REPO_ROOT}/defines/dev-images/entrypoint.sh" \
    "${TARGET_DIR}"

cp \
    "${REPO_ROOT}/defines.make" \
    "${REPO_ROOT}/package_versions.bzl" \
    "${REPO_ROOT}/.bazelversion" \
    "${REPO_ROOT}/omd/strip_binaries" \
    "${TARGET_DIR}"
