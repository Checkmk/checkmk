#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Runs inside the gcc-toolchain-builder image (see Dockerfile and build.sh).
# Expects TARGET, TARBALL_NAME, and GDB_TARBALL_NAME in the environment, the
# defconfig bind-mounted at /input/defconfig, and an output directory
# bind-mounted at /output.
set -e -o pipefail

# ct-ng only picks up a config at samples/<name>/crosstool.config relative to its cwd (its "local sample" mechanism).
mkdir -p "samples/${TARGET}"
cp /input/defconfig "samples/${TARGET}/crosstool.config"
ct-ng "${TARGET}"
ct-ng build

toolchain_dir="${HOME}/x-tools/${TARGET}"

tar --sort=name --owner=0 --group=0 --numeric-owner \
    --mtime='2026-01-01 00:00:00Z' \
    -C "$(dirname "${toolchain_dir}")" -cf - "${TARGET}" |
    xz -T0 -6 >"/output/${TARBALL_NAME}"

tar --sort=name --owner=0 --group=0 --numeric-owner \
    --mtime='2026-01-01 00:00:00Z' \
    -C "${toolchain_dir}/bin" -cf - "${TARGET}-gdb" |
    xz -T0 -6 >"/output/${GDB_TARBALL_NAME}"
