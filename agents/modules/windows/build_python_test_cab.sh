#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The action of python_test_cab (python_cab.bzl): the interpreter of
# python-3.cab with the stdlib kept and the test closure in its base
# site-packages, the harness Python of the Windows agent's pytest suites.
#
# Usage: build_python_test_cab.sh --out CAB --cab-lib FILE
#            --python-version 3.14.7 --python-tree DIR --pip-offline BIN
#            --pack-cab BIN
#            [--wheel WHL]... [--requirement PIN]...
#
# Paths are relative to the exec root, the working directory.

set -euo pipefail

exec_root=$PWD
wheels=()
requirements=()
while [ $# -gt 0 ]; do
    case "$1" in
        --out) out="$2" ;;
        --cab-lib) cab_lib="$2" ;;
        --python-version) python_version="$2" ;;
        --python-tree) python_tree="$2" ;;
        --pip-offline) pip_offline="$2" ;;
        --pack-cab) pack_cab="$2" ;;
        --wheel) wheels+=("$2") ;;
        --requirement) requirements+=("$2") ;;
        *)
            echo "error: unknown argument: $1" >&2
            exit 2
            ;;
    esac
    shift 2
done

# shellcheck disable=SC1090,SC1091 # cab_lib.sh, see python_cab.bzl
source "$cab_lib"

# 1. A writable copy of the extracted interpreter, and the wheels.
cab_setup "$python_tree" "${wheels[@]}"

# 2. The closure, straight into the base interpreter's site-packages: no venv,
# the harness calls this python.exe by its path. site processes the .pth files
# there (pywin32's among them) at startup. Unlike python-3.cab, the stdlib
# stays whole: pytest needs unittest.
"$exec_root/$pip_offline" --wheel-dir "$WHEELDIR" --python-version "$python_version" \
    --no-compile --target "$PY_DIR/Lib/site-packages" "${requirements[@]}"
# The cross-platform install puts POSIX console scripts there, with the build
# interpreter's path in their shebang; nothing runs them. Drop them and their
# RECORD lines, whose hashes would carry that path into the cab.
rm -rf "$PY_DIR/Lib/site-packages/bin"
sed -i '\#^\.\./\.\./bin/#d' "$PY_DIR"/Lib/site-packages/*.dist-info/RECORD
rm -f "$PY_DIR/Lib/site-packages/PyWin32.chm"

# 3. Bytecode caches.
cab_strip_bytecode

cab_check_no_build_paths

# 4. Pack.
"$exec_root/$pack_cab" --root "$PY_DIR" --out "$exec_root/$out"
