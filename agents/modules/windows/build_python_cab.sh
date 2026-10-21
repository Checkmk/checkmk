#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The action of python_cab (python_cab.bzl): builds the agent's python-3.cab
# in the shape production's Windows build gave it.
#
# Usage: build_python_cab.sh --workdir DIR --out CAB --py-short 314
#            --py-major-minor 3.14 --extract-msi BIN --msiinfo BIN
#            --cabextract BIN --libmsi LIB --pip-offline BIN
#            --make-exe-wrappers BIN --pack-cab BIN --pip-requirement PIN
#            --wrapper-shebang PATH --pyvenv-cfg FILE --postinstall FILE
#            [--requirement PIN]... [--venv-script FILE]...
#            [--wheel WHL]... [--msi MSI]...
#
# Paths are relative to the exec root, the working directory.

set -euo pipefail

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
requirements=()
venv_scripts=()
wheels=()
msis=()
while [ $# -gt 0 ]; do
    case "$1" in
        --workdir) workdir="$2" ;;
        --out) out="$2" ;;
        --py-short) py_short="$2" ;;
        --py-major-minor) py_major_minor="$2" ;;
        --extract-msi) extract_msi="$2" ;;
        --msiinfo) msiinfo="$2" ;;
        --cabextract) cabextract="$2" ;;
        --libmsi) libmsi="$2" ;;
        --pip-offline) pip_offline="$2" ;;
        --make-exe-wrappers) make_exe_wrappers="$2" ;;
        --pack-cab) pack_cab="$2" ;;
        --pip-requirement) pip_requirement="$2" ;;
        --wrapper-shebang) wrapper_shebang="$2" ;;
        --pyvenv-cfg) pyvenv_cfg="$2" ;;
        --postinstall) postinstall="$2" ;;
        --requirement) requirements+=("$2") ;;
        --venv-script) venv_scripts+=("$exec_root/$2") ;;
        --wheel) wheels+=("$2") ;;
        --msi) msis+=("$exec_root/$2") ;;
        *)
            echo "error: unknown argument: $1" >&2
            exit 2
            ;;
    esac
    shift 2
done

rm -rf "$workdir"
PY_DIR="$workdir/py"
WHEELDIR="$workdir/wheels"
mkdir -p "$PY_DIR" "$WHEELDIR"

# msiinfo is dynamically linked against libmsi.so.0.  Bazel ships the
# unversioned file libmsi.so.0.0.0; the loader needs to find it as the
# SONAME libmsi.so.0: create the symlink alongside.
libmsi_dir=$(dirname "$exec_root/$libmsi")
ln -sf "$(basename "$libmsi")" "$libmsi_dir/libmsi.so.0"

# Stage the pinned win_amd64 wheel closure into a pip --find-links dir; both
# pip installs below resolve against it offline (--no-index).
for w in "${wheels[@]}"; do
    cp "$w" "$WHEELDIR/"
done

# 1. Extract every MSI into the install-root tree using the Python
# msiextract that drives @msitools' msiinfo and @cabextract.
"$exec_root/$extract_msi" \
    --msiinfo "$exec_root/$msiinfo" \
    --cabextract "$exec_root/$cabextract" \
    --libmsi-dir "$libmsi_dir" \
    --directory "$PY_DIR" \
    "${msis[@]}"

# Sanity-check the python interpreter landed where we expect.
if [ ! -f "$PY_DIR/python.exe" ] || [ ! -f "$PY_DIR/python$py_short.dll" ]; then
    echo "error: python.exe / python$py_short.dll not found after msiextract" >&2
    find "$PY_DIR" -maxdepth 2 | head -50 >&2
    exit 1
fi

# 2. Give the base interpreter its pip.  pip.msi has an empty File table
# (the python.org installer bootstraps via a CustomAction msiextract can't
# replay), so install the pinned pip wheel directly, by name, so pip
# writes no direct_url.json pointing at build-machine paths.
"$exec_root/$pip_offline" "$WHEELDIR" install \
    --no-index \
    --find-links "$WHEELDIR" \
    --platform win_amd64 \
    --python-version "$py_major_minor" \
    --implementation cp \
    --abi "cp$py_short" \
    --only-binary=:all: \
    --no-warn-script-location \
    --target "$PY_DIR/Lib/site-packages" \
    "$pip_requirement"

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
"$exec_root/$pip_offline" "$WHEELDIR" install \
    --no-index \
    --find-links "$WHEELDIR" \
    --platform win_amd64 \
    --python-version "$py_major_minor" \
    --implementation cp \
    --abi "cp$py_short" \
    --only-binary=:all: \
    --no-warn-script-location \
    --target "$VENV/Lib/site-packages" \
    "${requirements[@]}"

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
    --shebang "$wrapper_shebang" \
    --fixup-records "$VENV/Lib/site-packages" \
    --fixup-records "$PY_DIR/Lib/site-packages"
if [ -d "$VENV/Lib/site-packages/bin" ]; then
    find "$VENV/Lib/site-packages/bin" -name '*.py' -exec cp {} "$VENV/Scripts/" \;
    rm -rf "$VENV/Lib/site-packages/bin"
fi

# 5. Write the production-shape pyvenv.cfg.
cp "$exec_root/$pyvenv_cfg" "$VENV/pyvenv.cfg"

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

# Installing by name from --find-links must not leave PEP 610 direct-url
# metadata (it would leak build paths and break reproducibility); fail
# loudly if pip's behaviour ever changes.
if find "$PY_DIR" -name direct_url.json | grep -q .; then
    echo "error: direct_url.json in the install tree leaks build paths:" >&2
    find "$PY_DIR" -name direct_url.json >&2
    exit 1
fi

# Bytecode caches.
find "$PY_DIR" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
find "$PY_DIR" -name '*.pyc' -delete 2>/dev/null || true

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

# 8. Pack into a cabinet via the vendored @cabarchive Python writer.
"$exec_root/$pack_cab" --root "$PY_DIR" --out "$exec_root/$out"
