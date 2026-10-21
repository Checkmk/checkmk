#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The action of python_cab (python_cab.bzl): builds the agent's python-3.cab
# in the shape production's Windows build gave it.
#
# Usage: build_python_cab.sh --out CAB --cab-lib FILE --python-version 3.14.7
#            --python-tree DIR --pip-offline BIN --make-exe-wrappers BIN
#            --pack-cab BIN --pip-requirement PIN --postinstall FILE
#            [--wheel WHL]... [--requirement PIN]... [--venv-script FILE]...
#
# Paths are relative to the exec root, the working directory.

set -euo pipefail

# Production's pyvenv.cfg points home at the agent's install path on the
# target host.  See clean_environment.cmd.
PYVENV_HOME='C:\ProgramData\checkmk\agent\modules\python-3'

# Interpreter the generated .exe wrappers exec at runtime: the production
# install path (see make_exe_wrappers.py for why not the build machine's).
WRAPPER_SHEBANG="$PYVENV_HOME"'\.venv\Scripts\python.exe'

# Stdlib subtrees to strip from the *base* interpreter, ported from
# clean_environment.cmd.  ensurepip is stripped because production's CAB
# ships without it (its phase 2 removes what phase 1 kept).
BASE_LIB_STRIP=(test unittest idlelib turtledemo tkinter venv ensurepip sqlite3)

# Loose files at the install root that production strips: LICENSE.txt,
# NEWS.txt, leftover MSI files (defensive; msiextract shouldn't drop these)
# and so on.
ROOT_FILE_STRIP_GLOBS=("*.txt" "*.msi" "Pipfile.*" "python-3.cab" "python-3.8.cab" "ucrtbase.dll" "api-ms-win-*.dll")

# Directories at the install root that production strips (not Lib / not DLLs).
ROOT_DIR_STRIP=(tools include libs Scripts tcl Tools)

# Production ships these into .venv/Scripts/ so the venv interpreter can
# resolve the UCRT runtime on a host without it installed system-wide.
UCRT_RUNTIME=(
    api-ms-win-crt-conio-l1-1-0.dll
    api-ms-win-crt-convert-l1-1-0.dll
    api-ms-win-crt-environment-l1-1-0.dll
    api-ms-win-crt-filesystem-l1-1-0.dll
    api-ms-win-crt-heap-l1-1-0.dll
    api-ms-win-crt-locale-l1-1-0.dll
    api-ms-win-crt-math-l1-1-0.dll
    api-ms-win-crt-multibyte-l1-1-0.dll
    api-ms-win-crt-private-l1-1-0.dll
    api-ms-win-crt-process-l1-1-0.dll
    api-ms-win-crt-runtime-l1-1-0.dll
    api-ms-win-crt-stdio-l1-1-0.dll
    api-ms-win-crt-string-l1-1-0.dll
    api-ms-win-crt-time-l1-1-0.dll
    api-ms-win-crt-utility-l1-1-0.dll
    ucrtbase.dll
)

exec_root=$PWD
wheels=()
requirements=()
venv_scripts=()
while [ $# -gt 0 ]; do
    case "$1" in
        --out) out="$2" ;;
        --cab-lib) cab_lib="$2" ;;
        --python-version) python_version="$2" ;;
        --python-tree) python_tree="$2" ;;
        --pip-offline) pip_offline="$2" ;;
        --make-exe-wrappers) make_exe_wrappers="$2" ;;
        --pack-cab) pack_cab="$2" ;;
        --pip-requirement) pip_requirement="$2" ;;
        --postinstall) postinstall="$2" ;;
        --wheel) wheels+=("$2") ;;
        --requirement) requirements+=("$2") ;;
        --venv-script) venv_scripts+=("$exec_root/$2") ;;
        *)
            echo "error: unknown argument: $1" >&2
            exit 2
            ;;
    esac
    shift 2
done

py_major_minor=${python_version%.*}
py_short=${py_major_minor/./}

# shellcheck disable=SC1090,SC1091 # cab_lib.sh, see python_cab.bzl
source "$cab_lib"

# 1. A writable copy of the extracted interpreter, and the wheels.
cab_setup "$python_tree" "${wheels[@]}"

# 2. Give the base interpreter its pip.  pip.msi has an empty File table
# (the python.org installer bootstraps via a CustomAction msiextract can't
# replay), so install the pinned pip wheel directly, by name, so pip
# writes no direct_url.json pointing at build-machine paths.
"$exec_root/$pip_offline" --wheel-dir "$WHEELDIR" --python-version "$python_version" \
    --target "$PY_DIR/Lib/site-packages" "$pip_requirement"

# 3. Hand-construct the .venv/ tree the way production's virtualenv laid it
# out.  Scripts/ gets a copy of the interpreter, its runtime DLLs, and the
# stdlib extension modules (virtualenv mirrored the base DLLs/ payload so
# the venv works even if DLL search order quirks hide the base copies).
VENV="$PY_DIR/.venv"
mkdir -p "$VENV/Scripts" "$VENV/Lib/site-packages"

cp "$PY_DIR/python.exe" "$VENV/Scripts/python.exe"
cp "$PY_DIR/pythonw.exe" "$VENV/Scripts/pythonw3.exe"
[ -f "$PY_DIR/python$py_short.dll" ] && cp "$PY_DIR/python$py_short.dll" "$VENV/Scripts/"
[ -f "$PY_DIR/python3.dll" ] && cp "$PY_DIR/python3.dll" "$VENV/Scripts/"
[ -f "$PY_DIR/vcruntime140.dll" ] && cp "$PY_DIR/vcruntime140.dll" "$VENV/Scripts/"
[ -f "$PY_DIR/vcruntime140_1.dll" ] && cp "$PY_DIR/vcruntime140_1.dll" "$VENV/Scripts/"
rm "$PY_DIR"/DLLs/sqlite3.dll
rm "$PY_DIR"/DLLs/_sqlite3.pyd
cp "$PY_DIR"/DLLs/*.pyd "$PY_DIR"/DLLs/*.dll "$VENV/Scripts/"

# The venv (re)launchers; lib.msi ships them under Lib/venv/scripts/nt
# (harvest before BASE_LIB_STRIP removes Lib/venv).  python3/python3.exe
# are the launcher under the names virtualenv seeded.
VENV_NT="$PY_DIR/Lib/venv/scripts/nt"
if [ ! -f "$VENV_NT/venvlauncher.exe" ] || [ ! -f "$VENV_NT/venvwlauncher.exe" ]; then
    echo "error: venv launchers not found under Lib/venv/scripts/nt" >&2
    exit 1
fi
cp "$VENV_NT/venvlauncher.exe" "$VENV/Scripts/venvlauncher.exe"
cp "$VENV_NT/venvlauncher.exe" "$VENV/Scripts/python3.exe"
cp "$VENV_NT/venvlauncher.exe" "$VENV/Scripts/python3"
cp "$VENV_NT/venvwlauncher.exe" "$VENV/Scripts/venvwlauncher.exe"

# UCRT redistributables alongside the venv python so it boots on hosts
# without a system-wide UCRT.
for f in "${UCRT_RUNTIME[@]}"; do
    [ -f "$PY_DIR/$f" ] && cp "$PY_DIR/$f" "$VENV/Scripts/"
done

# Activation scripts (production paths baked in; see venv_scripts/).  The
# .tmpl suffix only keeps repo formatters/linters away; strip it on copy.
for f in "${venv_scripts[@]}"; do
    cp "$f" "$VENV/Scripts/$(basename "$f" .tmpl)"
done

# 4. Install the locked closure into .venv/Lib/site-packages, offline.
# Every name==version pin is an explicit argument, so each dist-info gets
# a REQUESTED marker, exactly what the historic pipenv flow produced.
"$exec_root/$pip_offline" --wheel-dir "$WHEELDIR" --python-version "$python_version" \
    --target "$VENV/Lib/site-packages" "${requirements[@]}"

# ... except pip itself: production's pip was seeded by virtualenv, which
# writes no REQUESTED.
rm -f "$VENV/Lib/site-packages"/pip-*.dist-info/REQUESTED

# Console entry points: the cross-platform pip install drops POSIX scripts
# into <target>/bin/; production ships distlib .exe launchers in Scripts/
# instead.  Regenerate those, fix up the RECORDs, and drop bin/ (keeping
# its plain-script payloads like a native Windows install does).
"$exec_root/$make_exe_wrappers" \
    --pip-wheel "$WHEELDIR" \
    --scripts-dir "$VENV/Scripts" \
    --python-major-minor "$py_major_minor" \
    --shebang "$WRAPPER_SHEBANG" \
    --fixup-records "$VENV/Lib/site-packages" \
    --fixup-records "$PY_DIR/Lib/site-packages"
if [ -d "$VENV/Lib/site-packages/bin" ]; then
    find "$VENV/Lib/site-packages/bin" -name '*.py' -exec cp {} "$VENV/Scripts/" \;
    rm -rf "$VENV/Lib/site-packages/bin"
fi

# 5. Write the production-shape pyvenv.cfg.
printf 'home = %s\nversion_info = %s\ninclude-system-site-packages = false\n' \
    "$PYVENV_HOME" "$python_version" >"$VENV/pyvenv.cfg"

# 6. Strip from the base interpreter what production strips (the union of
# clean_environment.cmd's phase-1 and phase-2 cleanups).
for d in "${BASE_LIB_STRIP[@]}"; do
    rm -rf "$PY_DIR/Lib/$d"
done
for d in "${ROOT_DIR_STRIP[@]}"; do
    rm -rf "${PY_DIR:?}/$d"
done
(cd "$PY_DIR" && for g in "${ROOT_FILE_STRIP_GLOBS[@]}"; do
    # nullglob via 'find -name' so missing files don't fail the loop.
    find . -maxdepth 1 -name "$g" -delete 2>/dev/null || true
done)
# clean_environment.cmd also dels DLLs/*.ico and DLLs/*.cat, but production
# still ships them (the forward-slash del no-ops on cmd.exe): keep them.
rm -f "$PY_DIR/Lib/turtle.py" 2>/dev/null || true
# The base pip's entry-point scripts land under bin/; production has no
# base bin/ (its Scripts/ equivalent is stripped via ROOT_DIR_STRIP above).
rm -rf "$PY_DIR/Lib/site-packages/bin" 2>/dev/null || true

# Bytecode caches.
cab_strip_bytecode

# Strip pipenv/virtualenv/setuptools subtrees anywhere in the tree
# (clean_environment.cmd does this with a recursive dir loop).
find "$PY_DIR" -type d \( \
    -name 'pipenv' -o -name 'pipenv-*' -o \
    -name 'virtualenv' -o -name 'virtualenv-*' -o \
    -name 'setuptools' -o -name 'setuptools-*' \
    \) -exec rm -rf {} + 2>/dev/null || true

# Production-specific venv strips.
rm -f "$VENV/.project" 2>/dev/null || true
rm -rf "$VENV/Lib/tcl8.6" 2>/dev/null || true
rm -f "$VENV/Lib/site-packages/PyWin32.chm" 2>/dev/null || true
rm -f "$VENV/Scripts/pythonw.exe" 2>/dev/null || true

# 7. Drop the agent's postinstall.cmd at the install root.  Production
# ships both postinstall.cmd and pyvenv.cfg with CRLF line endings.
cp "$exec_root/$postinstall" "$PY_DIR/postinstall.cmd"
sed -i 's/\r$//; s/$/\r/' "$PY_DIR/postinstall.cmd" "$VENV/pyvenv.cfg"

cab_check_no_build_paths

# 8. Pack into a cabinet via the vendored @cabarchive Python writer.
"$exec_root/$pack_cab" --root "$PY_DIR" --out "$exec_root/$out"
