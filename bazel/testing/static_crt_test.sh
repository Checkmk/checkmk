#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Assert that a cross-compiled Windows PE binary does not import any CRT
# DLL, i.e. the CRT is fully statically linked. The Rust side gets
# -Ctarget-feature=+crt-static from a platform flag on
# //bazel/platforms:x86_64-windows-msvc and the C side relies on the
# /MD -> /MT compile arg declared in //bazel/toolchains/cc/xwin/args, so a
# regression in either shows up here as a
# vcruntime*/msvcr*/ucrtbase/msvcp*/api-ms-win-crt-* import.

set -euo pipefail

RUNFILES="${RUNFILES_DIR:-$0.runfiles}"
READOBJ="$RUNFILES/$1"
EXE="$RUNFILES/$2"

IMPORTS=$("$READOBJ" --coff-imports "$EXE" | awk '/Name:/ {print tolower($2)}' | sort -u)

echo "imports of $(basename "$EXE"):"
echo "$IMPORTS"

if ! echo "$IMPORTS" | grep -Fxq 'kernel32.dll'; then
    echo "FAIL: kernel32.dll not among the imports - not a parsed PE import table?" >&2
    exit 1
fi

BAD=$(echo "$IMPORTS" | grep -E '^(vcruntime|msvcr|ucrtbase|msvcp|api-ms-win-crt-)' || true)
if [ -n "$BAD" ]; then
    echo "FAIL: dynamic CRT imports found (CRT must be statically linked):" >&2
    echo "$BAD" >&2
    exit 1
fi

echo "OK: no dynamic CRT imports"
