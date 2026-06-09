#!/bin/bash
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# SUP-28810: the `openssl` crate (features = ["vendored"]) used by cmk-agent-ctl
# and mk-sql builds OpenSSL via `openssl-src`, which configures it with
# --prefix=<crate OUT_DIR>; OpenSSL bakes that per-build sandbox path into
# libcrypto's ENGINESDIR/MODULESDIR/OPENSSLDIR strings, which then leak into the
# statically linked agent binaries (tripping package_validator).
#
# Source this file and call `setup_vendored_openssl_src_patch <repo_dir>`. It
# applies patches/openssl-src-stable-paths.patch to a copy of the locked
# openssl-src crate to configure stable FHS paths (--prefix=/usr, real artifacts
# staged via DESTDIR) and exports:
#   * OPENSSL_CONFIG_DIR        - stable OPENSSLDIR for the vendored build
#   * OPENSSL_SRC_PATCH_CONFIG  - `cargo --config` value redirecting openssl-src
#     at the patched copy, e.g.  cargo build ... --config "$OPENSSL_SRC_PATCH_CONFIG"

setup_vendored_openssl_src_patch() {
    local host_dir="$1/packages/host"
    local pkg_name="${2:-shared}"
    local lock="${host_dir}/Cargo.lock"
    local staging="${host_dir}/.sup28810/${pkg_name}/openssl-src"
    local patch_file="${host_dir}/patches/openssl-src-stable-paths.patch"
    local version crate

    version="$(sed -n '/^name = "openssl-src"$/{n;s/^version = "\(.*\)"$/\1/p;}' "${lock}" | head -n1)"
    test -n "${version}" || failure "openssl-src version not found in Cargo.lock"

    crate="$(find "${CARGO_HOME:-${HOME}/.cargo}/registry/cache" -name "openssl-src-${version}.crate" 2>/dev/null | head -n1)"
    if test -z "${crate}"; then
        (cd "${host_dir}" && cargo fetch --quiet) || failure "cargo fetch failed"
        crate="$(find "${CARGO_HOME:-${HOME}/.cargo}/registry/cache" -name "openssl-src-${version}.crate" 2>/dev/null | head -n1)"
    fi
    test -n "${crate}" || failure "openssl-src-${version}.crate not in cargo cache"

    rm -rf "${staging}"
    mkdir -p "${staging}"
    tar xzf "${crate}" -C "${staging}" --strip-components=1

    # Configure with a stable --prefix, install into the crate OUT_DIR via DESTDIR,
    # and report the relocated usr/{lib,bin,include} layout (see the patch header).
    # patch fails if any hunk's context is gone (e.g. after a crate upgrade) so a
    # silently-unpatched build errors out rather than shipping leaked paths.
    patch -p1 -d "${staging}" <"${patch_file}" || failure "openssl-src patch did not apply (crate layout changed?)"

    # The patched copy keeps the locked version so the [patch] replaces the locked
    # registry source in place; that drops its source/checksum from Cargo.lock, so
    # restore the committed lock on exit to keep the tree clean.
    cp "${lock}" "${host_dir}/.sup28810/Cargo.lock.committed"
    # shellcheck disable=SC2064
    trap "cp -f '${host_dir}/.sup28810/Cargo.lock.committed' '${lock}'" EXIT

    export OPENSSL_CONFIG_DIR="/etc/ssl"
    # shellcheck disable=SC2089
    OPENSSL_SRC_PATCH_CONFIG="patch.crates-io.openssl-src.path=\"${staging}\""
    # shellcheck disable=SC2090
    export OPENSSL_SRC_PATCH_CONFIG
}
