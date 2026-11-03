#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The steps the cab builds of python_cab.bzl share, sourced by
# build_python_cab.sh and build_python_test_cab.sh. Paths are relative to the
# exec root, the working directory.

# Usage: cab_setup PYTHON_TREE WHEEL...
#
# Sets up the scratch dir workdir, which an EXIT trap removes (replacing any
# the caller set): PY_DIR becomes a writable copy of the extracted
# interpreter (python_msi_tree), WHEELDIR the wheels, staged as pip's
# --find-links dir. cab_check_no_build_paths reads workdir.
# shellcheck disable=SC2034 # sets PY_DIR and WHEELDIR for the sourcing scripts
cab_setup() {
    workdir=$(mktemp -d)
    trap 'rm -rf "$workdir"' EXIT
    PY_DIR="$workdir/py"
    WHEELDIR="$workdir/wheels"
    mkdir "$WHEELDIR"
    cp -RL "$1" "$PY_DIR"
    chmod -R u+w "$PY_DIR"
    shift
    cp "$@" "$WHEELDIR/"
}

# Usage: cab_check_no_build_paths
#
# Fails if PY_DIR leaks a build path into the cab.
cab_check_no_build_paths() {
    # Installing by name from --find-links must not leave PEP 610 direct-url
    # metadata; fail loudly if pip's behaviour ever changes.
    if find "$PY_DIR" -name direct_url.json | grep -q .; then
        echo "error: direct_url.json in the install tree leaks build paths:" >&2
        find "$PY_DIR" -name direct_url.json >&2
        exit 1
    fi
    # Look for the output base, not just the exec root: a realpath that
    # escapes the sandbox lands in the output base's execroot/ or external/.
    # (Under remote execution neither pattern matches and this is the exec
    # root.) And for the scratch dir, where pip installed.
    local build_root=${PWD%%/sandbox/*}
    build_root=${build_root%%/execroot/*}
    if grep -rlF -e "$build_root" -e "$workdir" "$PY_DIR"; then
        echo "error: these files in the install tree carry the build path" >&2
        exit 1
    fi
}

# Usage: cab_strip_bytecode
#
# Removes the bytecode caches from PY_DIR.
cab_strip_bytecode() {
    find "$PY_DIR" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
    find "$PY_DIR" -name '*.pyc' -delete 2>/dev/null || true
}
