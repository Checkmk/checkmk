# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Starlark rule that builds the Windows ``python-3.cab`` on Linux.

The CAB has the same shape as the one historically produced by
``agents/modules/windows/Makefile`` on a Windows build node, but the build
runs on Linux with no Wine / MSBuild / makecab.exe in the picture, and all
tools are Bazel-managed:

* ``extract_msi.py`` (pure Python) drives ``msiinfo`` from ``@msitools``
  and the vendored ``@cabarchive`` to unpack the per-feature MSIs.
* ``pip_offline.py`` installs the ``win_amd64`` wheels *offline* from the
  fetch-phase ``@windows_python_wheels`` closure with
  ``--no-index --find-links`` (cross-platform flags still select win_amd64).
  It runs under the repo's hermetic CPython (same 3.13 line as the CAB), so
  pip-written metadata (RECORD bytecode entries) matches the CAB's Python.
* ``.venv/`` is laid down by hand to match production: interpreter + runtime
  DLL copies, the stdlib extension modules virtualenv mirrored into
  ``Scripts/``, the venv launchers from ``Lib/venv/scripts/nt``, generated
  console-script ``.exe`` wrappers (``make_exe_wrappers.py``), and the
  activation scripts under ``venv_scripts/``.
* ``pack_cab.py`` (vendored ``@cabarchive`` writer) produces the cabinet.

The action takes no network: the MSIs come from five ``http_file`` repos and
the wheels from ``@windows_python_wheels`` (a ``repository_rule`` that downloads
the sha256-pinned closure at the fetch phase), all declared in ``MODULE.bazel``.
Refresh the MSI pins via ``agents/modules/windows/refresh_msi_pins.py`` and the
wheel pins via ``agents/modules/windows/refresh_wheel_pins.py`` on a bump.

Known deliberate deviations from the historic Windows-built CAB (all dead
weight with no source in the pinned python.org MSI set):

* no ``py.exe`` / ``pyw.exe`` / ``pyshellext.dll`` in ``.venv/Scripts`` — the
  py-launcher stopped shipping MSIs with CPython 3.13; the launcher is
  useless inside the agent's venv anyway.
* no ``_tkinter.pyd`` / ``xxlimited*.pyd`` / ``zlib1.dll`` in
  ``.venv/Scripts`` — build-from-source artifacts; tkinter's stdlib package
  is stripped from the CAB, so the old copies could never import.
* no virtualenv bookkeeping files (``.gitignore``, ``CACHEDIR.TAG``,
  ``_virtualenv.py``/``.pth``, ``pip-*.virtualenv``) and no pipenv/virtualenv
  tool spill-over in the base ``Lib/site-packages``.
"""

# Stdlib subtrees to strip from the *base* interpreter, ported from
# agents/modules/windows/clean_environment.cmd (phase 1 + phase 2 cleanups).
# ``ensurepip`` is in this list because production's CAB ships without it,
# even though clean_environment.cmd's phase 1 keeps it; phase 2 does
# ``rd /Q /S Lib\ensurepip`` which removes it.
_BASE_LIB_STRIP = [
    "test",
    "unittest",
    "idlelib",
    "turtledemo",
    "tkinter",
    "venv",
    "ensurepip",
]

# Loose files at the install root that production strips.
_ROOT_FILE_STRIP_GLOBS = [
    "*.txt",  # LICENSE.txt, NEWS.txt
    "*.msi",  # leftover MSI files (defensive; msiextract shouldn't drop these)
    "Pipfile.*",
    "python-3.cab",
    "python-3.8.cab",
    "ucrtbase.dll",
    "api-ms-win-*.dll",
]

# Directories at the install root that production strips (not ``Lib`` / not ``DLLs``).
_ROOT_DIR_STRIP = [
    "tools",
    "include",
    "libs",
    "Scripts",
    "tcl",
    "Tools",
]

# Production ships these into ``.venv/Scripts/`` so the venv interpreter
# can resolve the UCRT runtime on a host without it installed system-wide.
_UCRT_RUNTIME_GLOBS = [
    "api-ms-win-crt-conio-l1-1-0.dll",
    "api-ms-win-crt-convert-l1-1-0.dll",
    "api-ms-win-crt-environment-l1-1-0.dll",
    "api-ms-win-crt-filesystem-l1-1-0.dll",
    "api-ms-win-crt-heap-l1-1-0.dll",
    "api-ms-win-crt-locale-l1-1-0.dll",
    "api-ms-win-crt-math-l1-1-0.dll",
    "api-ms-win-crt-multibyte-l1-1-0.dll",
    "api-ms-win-crt-private-l1-1-0.dll",
    "api-ms-win-crt-process-l1-1-0.dll",
    "api-ms-win-crt-runtime-l1-1-0.dll",
    "api-ms-win-crt-stdio-l1-1-0.dll",
    "api-ms-win-crt-string-l1-1-0.dll",
    "api-ms-win-crt-time-l1-1-0.dll",
    "api-ms-win-crt-utility-l1-1-0.dll",
    "ucrtbase.dll",
]

# Production's pyvenv.cfg is three lines, with the home pointing at the
# agent's install path on the target host.  See clean_environment.cmd.
_PYVENV_HOME = "C:\\ProgramData\\checkmk\\agent\\modules\\python-3"

# Interpreter the generated .exe wrappers exec at runtime.  The historic
# Windows build baked the *build machine's* venv path here, which broke the
# wrappers on customer hosts; we bake the production path.
_WRAPPER_SHEBANG = _PYVENV_HOME + "\\.venv\\Scripts\\python.exe"

def _python_version_short(version):
    # "3.13.13" -> "313"
    parts = version.split(".")
    if len(parts) < 2:
        fail("python_version must be a dotted version like 3.13.13, got %r" % version)
    return parts[0] + parts[1]

def _python_cab_impl(ctx):
    cab = ctx.actions.declare_file(ctx.label.name + ".cab")

    workdir = cab.path + ".work"
    py_short = _python_version_short(ctx.attr.python_version)
    py_major_minor = ".".join(ctx.attr.python_version.split(".")[:2])  # "3.13"
    py_abi = "cp" + py_short  # "cp313"

    # The venv seeds pip (the historic flow's virtualenv did, so customers can
    # `.venv\Scripts\pip install` extra plugin deps); the same pinned wheel
    # also replaces the base interpreter's ensurepip bootstrap.
    pip_pins = [r for r in ctx.attr.requirements if r.startswith("pip==")]
    if len(pip_pins) != 1:
        fail("requirements must contain exactly one pip== pin, got %r" % ctx.attr.requirements)
    pip_requirement = pip_pins[0]

    # Production-shape 3-line pyvenv.cfg, written as a build input so we
    # avoid backslash-escape hazards inside the shell command.
    pyvenv_cfg = ctx.actions.declare_file(ctx.label.name + ".pyvenv.cfg")
    ctx.actions.write(
        output = pyvenv_cfg,
        content = "home = {home}\nversion_info = {ver}\ninclude-system-site-packages = false\n".format(
            home = _PYVENV_HOME,
            ver = ctx.attr.python_version,
        ),
    )

    postinstall = ctx.file.postinstall_cmd

    msis = [
        ctx.file.msi_ucrt,
        ctx.file.msi_core,
        ctx.file.msi_exe,
        ctx.file.msi_lib,
        ctx.file.msi_pip,
    ]
    msi_path_args = " ".join(['"$exec_root/{}"'.format(m.path) for m in msis])

    msiinfo = ctx.file.msiinfo
    libmsi = ctx.file.libmsi
    cabextract = ctx.file.cabextract
    extract_msi_run = ctx.attr.extract_msi[DefaultInfo].files_to_run
    pack_cab_run = ctx.attr.pack_cab[DefaultInfo].files_to_run
    pip_offline_run = ctx.attr.pip_offline[DefaultInfo].files_to_run
    make_exe_wrappers_run = ctx.attr.make_exe_wrappers[DefaultInfo].files_to_run

    requirements_args = " ".join([
        '"{}"'.format(req)
        for req in ctx.attr.requirements
    ])
    wheel_files = ctx.files.wheels
    wheel_path_args = " ".join(['"$exec_root/{}"'.format(w.path) for w in wheel_files])
    venv_script_files = ctx.files.venv_scripts
    venv_script_args = " ".join(['"$exec_root/{}"'.format(f.path) for f in venv_script_files])
    base_lib_strip = " ".join(_BASE_LIB_STRIP)
    root_dir_strip = " ".join(_ROOT_DIR_STRIP)
    root_file_strip = " ".join(['"%s"' % g for g in _ROOT_FILE_STRIP_GLOBS])
    ucrt_globs = " ".join(_UCRT_RUNTIME_GLOBS)

    cmd = """
set -euo pipefail

WORKDIR="{workdir}"
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"

PY_DIR="$WORKDIR/py"
mkdir -p "$PY_DIR"

# msiinfo is dynamically linked against libmsi.so.0.  Bazel ships the
# unversioned file libmsi.so.0.0.0; the loader needs to find it as the
# SONAME libmsi.so.0 — create the symlink alongside.
LIBMSI_ABS="$exec_root/{libmsi}"
LIBMSI_DIR=$(dirname "$LIBMSI_ABS")
ln -sf "$(basename "$LIBMSI_ABS")" "$LIBMSI_DIR/libmsi.so.0"

# Stage the pinned win_amd64 wheel closure into a pip --find-links dir; both
# pip installs below resolve against it offline (--no-index).
WHEELDIR="$WORKDIR/wheels"
mkdir -p "$WHEELDIR"
for w in {wheel_paths}; do
    cp "$w" "$WHEELDIR/"
done

# 1. Extract every MSI into the install-root tree using the Python
# msiextract that drives @msitools' msiinfo and @cabextract.
"$exec_root/{extract_msi}" \\
    --msiinfo "$exec_root/{msiinfo}" \\
    --cabextract "$exec_root/{cabextract}" \\
    --libmsi-dir "$LIBMSI_DIR" \\
    --directory "$PY_DIR" \\
    {msi_paths}

# Sanity-check the python interpreter landed where we expect.
if [ ! -f "$PY_DIR/python.exe" ] || [ ! -f "$PY_DIR/python{py_short}.dll" ]; then
    echo "error: python.exe / python{py_short}.dll not found after msiextract" >&2
    find "$PY_DIR" -maxdepth 2 | head -50 >&2
    exit 1
fi

# 2. Give the base interpreter its pip.  pip.msi has an empty File table —
# the python.org installer runs ``python -m ensurepip`` via a CustomAction,
# which msiextract can't replay.  The historic flow then let pipenv upgrade
# the bootstrapped pip to the latest release, so we skip the bootstrap and
# install the pinned pip wheel directly (by name, so pip writes no
# direct_url.json pointing at build-machine paths).
"$exec_root/{pip_offline}" "$WHEELDIR" install \\
    --no-index \\
    --find-links "$WHEELDIR" \\
    --platform win_amd64 \\
    --python-version "{py_major_minor}" \\
    --implementation cp \\
    --abi "{py_abi}" \\
    --only-binary=:all: \\
    --no-warn-script-location \\
    --target "$PY_DIR/Lib/site-packages" \\
    "{pip_requirement}"

# 3. Hand-construct the .venv/ tree the way production's virtualenv laid it
# out.  Scripts/ gets a copy of the interpreter, its runtime DLLs, and the
# stdlib extension modules (virtualenv mirrored the base DLLs/ payload so
# the venv works even if DLL search order quirks hide the base copies).
VENV="$PY_DIR/.venv"
mkdir -p "$VENV/Scripts" "$VENV/Lib/site-packages"

cp "$PY_DIR/python.exe" "$VENV/Scripts/python.exe"
cp "$PY_DIR/pythonw.exe" "$VENV/Scripts/pythonw3.exe"
[ -f "$PY_DIR/python{py_short}.dll" ] && cp "$PY_DIR/python{py_short}.dll" "$VENV/Scripts/"
[ -f "$PY_DIR/python3.dll" ] && cp "$PY_DIR/python3.dll" "$VENV/Scripts/"
[ -f "$PY_DIR/vcruntime140.dll" ] && cp "$PY_DIR/vcruntime140.dll" "$VENV/Scripts/"
[ -f "$PY_DIR/vcruntime140_1.dll" ] && cp "$PY_DIR/vcruntime140_1.dll" "$VENV/Scripts/"
cp "$PY_DIR"/DLLs/*.pyd "$PY_DIR"/DLLs/*.dll "$VENV/Scripts/"

# The venv (re)launchers; lib.msi ships them under Lib/venv/scripts/nt
# (harvest before _BASE_LIB_STRIP removes Lib/venv).  python3/python3.exe
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
for f in {ucrt_globs}; do
    [ -f "$PY_DIR/$f" ] && cp "$PY_DIR/$f" "$VENV/Scripts/"
done

# Activation scripts (production paths baked in; see venv_scripts/).
# The .tmpl suffix only keeps repo formatters/linters away from the
# shipped-verbatim payloads; strip it on copy.
for f in {venv_scripts}; do
    cp "$f" "$VENV/Scripts/$(basename "$f" .tmpl)"
done

# 4. Install the locked closure into .venv/Lib/site-packages using the
# pinned pip in cross-platform mode, offline.  Every name==version pin is an
# explicit argument, so each dist-info gets a REQUESTED marker — exactly
# what the historic pipenv flow produced.
"$exec_root/{pip_offline}" "$WHEELDIR" install \\
    --no-index \\
    --find-links "$WHEELDIR" \\
    --platform win_amd64 \\
    --python-version "{py_major_minor}" \\
    --implementation cp \\
    --abi "{py_abi}" \\
    --only-binary=:all: \\
    --no-warn-script-location \\
    --target "$VENV/Lib/site-packages" \\
    {requirements_args}

# ... except pip itself: production's pip was seeded by virtualenv, which
# writes no REQUESTED.
rm -f "$VENV/Lib/site-packages"/pip-*.dist-info/REQUESTED

# Console entry points: pip's cross-platform --target install drops POSIX
# scripts into <target>/bin/.  Production ships distlib .exe launchers in
# Scripts/ instead — regenerate those, rewrite the RECORD lines that point
# at bin/, keep the plain-script payloads (pywin32_postinstall.py etc.)
# like a native Windows install does, and drop the bin/ dir.
"$exec_root/{make_exe_wrappers}" \\
    --pip-wheel "$WHEELDIR" \\
    --scripts-dir "$VENV/Scripts" \\
    --shebang '{wrapper_shebang}' \\
    --fixup-records "$VENV/Lib/site-packages" \\
    --fixup-records "$PY_DIR/Lib/site-packages"
if [ -d "$VENV/Lib/site-packages/bin" ]; then
    find "$VENV/Lib/site-packages/bin" -name '*.py' -exec cp {{}} "$VENV/Scripts/" \\;
    rm -rf "$VENV/Lib/site-packages/bin"
fi

# 5. Write the production-shape pyvenv.cfg.
cp "$exec_root/{pyvenv_cfg}" "$VENV/pyvenv.cfg"

# 6. Strip from the base interpreter what production strips.  See
# clean_environment.cmd; this list is the union of phase-1 and phase-2
# cleanups.
for d in {base_lib_strip}; do
    rm -rf "$PY_DIR/Lib/$d"
done
for d in {root_dir_strip}; do
    rm -rf "$PY_DIR/$d"
done
( cd "$PY_DIR" && for g in {root_file_strip}; do
    # nullglob via 'find -name' so missing files don't fail the loop.
    find . -maxdepth 1 -name "$g" -delete 2>/dev/null || true
done )
# NOTE: clean_environment.cmd contains ``del /Q DLLs/*.ico`` and
# ``del /Q DLLs/*.cat`` but the production reference CAB still ships
# py.ico, pyc.ico, pyd.ico, and python_lib.cat — the del's forward-slash
# path apparently no-ops on cmd.exe.  Keep them here to match production.
rm -f "$PY_DIR/Lib/turtle.py" 2>/dev/null || true
# The base pip's entry-point scripts land under <target>/bin/ as POSIX
# scripts; production has no base bin/ (its Scripts/ equivalent is stripped
# via _ROOT_DIR_STRIP above).
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
find "$PY_DIR" -name __pycache__ -type d -exec rm -rf {{}} + 2>/dev/null || true
find "$PY_DIR" -name '*.pyc' -delete 2>/dev/null || true

# Strip pipenv/virtualenv/setuptools subtrees anywhere in the tree
# (clean_environment.cmd does this with a recursive dir loop).
find "$PY_DIR" -type d \\( \\
    -name 'pipenv' -o -name 'pipenv-*' -o \\
    -name 'virtualenv' -o -name 'virtualenv-*' -o \\
    -name 'setuptools' -o -name 'setuptools-*' \\
\\) -exec rm -rf {{}} + 2>/dev/null || true

# Production-specific venv strips.
rm -f "$VENV/.project" 2>/dev/null || true
rm -rf "$VENV/Lib/tcl8.6" 2>/dev/null || true
rm -f "$VENV/Lib/site-packages/PyWin32.chm" 2>/dev/null || true
rm -f "$VENV/Scripts/pythonw.exe" 2>/dev/null || true

# 7. Drop the agent's postinstall.cmd at the install root.  Production
# ships both postinstall.cmd and pyvenv.cfg with CRLF line endings.
cp "$exec_root/{postinstall}" "$PY_DIR/postinstall.cmd"
sed -i 's/\\r$//; s/$/\\r/' "$PY_DIR/postinstall.cmd" "$VENV/pyvenv.cfg"

# 8. Pack into a cabinet via the vendored @cabarchive Python writer.
"$exec_root/{pack_cab}" --root "$PY_DIR" --out "$exec_root/{cab_out}"
""".format(
        workdir = workdir,
        msi_paths = msi_path_args,
        msiinfo = msiinfo.path,
        libmsi = libmsi.path,
        cabextract = cabextract.path,
        extract_msi = extract_msi_run.executable.path,
        pack_cab = pack_cab_run.executable.path,
        pip_offline = pip_offline_run.executable.path,
        make_exe_wrappers = make_exe_wrappers_run.executable.path,
        py_short = py_short,
        py_major_minor = py_major_minor,
        py_abi = py_abi,
        pip_requirement = pip_requirement,
        requirements_args = requirements_args,
        wheel_paths = wheel_path_args,
        venv_scripts = venv_script_args,
        wrapper_shebang = _WRAPPER_SHEBANG,
        base_lib_strip = base_lib_strip,
        root_dir_strip = root_dir_strip,
        root_file_strip = root_file_strip,
        ucrt_globs = ucrt_globs,
        postinstall = postinstall.path,
        pyvenv_cfg = pyvenv_cfg.path,
        cab_out = cab.path,
    )
    cmd = "exec_root=$PWD\n" + cmd

    ctx.actions.run_shell(
        outputs = [cab],
        inputs = msis + wheel_files + venv_script_files +
                 [postinstall, pyvenv_cfg, msiinfo, libmsi, cabextract],
        tools = [extract_msi_run, pack_cab_run, pip_offline_run, make_exe_wrappers_run],
        command = cmd,
        mnemonic = "PythonCab",
        progress_message = "Building Windows python-3.cab on Linux (%{label})",
        # No network: MSIs and wheels are fetched at the fetch phase and pip
        # installs offline (--no-index --find-links).
        use_default_shell_env = True,
    )

    return [DefaultInfo(files = depset([cab]))]

python_cab = rule(
    implementation = _python_cab_impl,
    attrs = {
        "cabextract": attr.label(
            mandatory = True,
            allow_single_file = True,
            cfg = "exec",
            doc = "cabextract binary filegroup from @cabextract.",
        ),
        "extract_msi": attr.label(
            mandatory = True,
            executable = True,
            cfg = "exec",
            doc = "py_binary that extracts an MSI into a directory tree.",
        ),
        "libmsi": attr.label(
            mandatory = True,
            allow_single_file = True,
            cfg = "exec",
            doc = "libmsi shared library filegroup from @msitools.",
        ),
        "make_exe_wrappers": attr.label(
            mandatory = True,
            executable = True,
            cfg = "exec",
            doc = "py_binary that generates the Windows console-script .exe wrappers.",
        ),
        "msi_core": attr.label(
            default = "@python_msi_core//file",
            allow_single_file = [".msi"],
        ),
        "msi_exe": attr.label(
            default = "@python_msi_exe//file",
            allow_single_file = [".msi"],
        ),
        "msi_lib": attr.label(
            default = "@python_msi_lib//file",
            allow_single_file = [".msi"],
        ),
        "msi_pip": attr.label(
            default = "@python_msi_pip//file",
            allow_single_file = [".msi"],
        ),
        "msi_ucrt": attr.label(
            default = "@python_msi_ucrt//file",
            allow_single_file = [".msi"],
        ),
        "msiinfo": attr.label(
            mandatory = True,
            allow_single_file = True,
            cfg = "exec",
            doc = "msiinfo binary filegroup from @msitools.",
        ),
        "pack_cab": attr.label(
            mandatory = True,
            executable = True,
            cfg = "exec",
            doc = "py_binary that packs a directory tree into a CAB via @cabarchive.",
        ),
        "pip_offline": attr.label(
            mandatory = True,
            executable = True,
            cfg = "exec",
            doc = "py_binary that runs the pinned pip offline under the hermetic interpreter.",
        ),
        "postinstall_cmd": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "Agent's postinstall.cmd, copied verbatim to the install root.",
        ),
        "python_version": attr.string(
            mandatory = True,
            doc = "Full CPython version (e.g. \"3.13.13\"); must match PYTHON_VERSION_WINDOWS in defines.make.",
        ),
        "requirements": attr.string_list(
            mandatory = True,
            doc = "Pinned name==version closure (from @windows_python_wheels//:requirements.bzl) " +
                  "installed into .venv/Lib/site-packages; must include exactly one pip== pin.",
        ),
        "venv_scripts": attr.label_list(
            allow_files = True,
            doc = "Static venv activation scripts copied into .venv/Scripts (see venv_scripts/).",
        ),
        "wheels": attr.label_list(
            allow_files = [".whl"],
            doc = "Pinned win_amd64/cp3xx wheel closure (the @windows_python_wheels " +
                  "fetch-phase repo) that 'requirements' is installed from offline.",
        ),
    },
)
