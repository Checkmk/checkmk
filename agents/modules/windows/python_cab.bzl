# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Starlark rule that builds the Windows ``python-3.cab`` on Linux.

The CAB has the same shape as the one historically produced by
``agents/modules/windows/Makefile`` on a Windows build node, but no
Wine / MSBuild / makecab.exe is involved: every tool the action runs is a
Bazel-managed input (see their py_binary targets in BUILD.bazel).

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

# Production's pyvenv.cfg is three lines, with the home pointing at the
# agent's install path on the target host.  See clean_environment.cmd.
_PYVENV_HOME = "C:\\ProgramData\\checkmk\\agent\\modules\\python-3"

# Interpreter the generated .exe wrappers exec at runtime — the production
# install path (see make_exe_wrappers.py for why not the build machine's).
_WRAPPER_SHEBANG = _PYVENV_HOME + "\\.venv\\Scripts\\python.exe"

def python_version_major_minor(version):
    # "3.13.14" -> "3.13", the part the cp3xx wheel ABI tag encodes
    parts = version.split(".")
    if len(parts) < 2:
        fail("python_version must be a dotted version like 3.13.13, got %r" % version)
    return parts[0] + "." + parts[1]

def _python_version_short(version):
    # "3.13.13" -> "313"
    return python_version_major_minor(version).replace(".", "")

def _py_platform_transition_impl(_settings, attr):
    return {
        "//command_line_option:platforms": str(attr.target_platform),
        "@rules_python//python/config_settings:python_version": python_version_major_minor(attr.python_version),
    }

_py_platform_transition = transition(
    implementation = _py_platform_transition_impl,
    inputs = [],
    outputs = [
        "//command_line_option:platforms",
        "@rules_python//python/config_settings:python_version",
    ],
)

def _py_platform_transition_filegroup_impl(ctx):
    return [DefaultInfo(
        files = depset(transitive = [src[DefaultInfo].files for src in ctx.attr.srcs]),
    )]

py_platform_transition_filegroup = rule(
    implementation = _py_platform_transition_filegroup_impl,
    attrs = {
        "python_version": attr.string(
            mandatory = True,
            doc = "CPython version whose major.minor selects the wheel ABI; " +
                  "a full version is accepted, the patch level is ignored.",
        ),
        "srcs": attr.label_list(
            allow_files = True,
            cfg = _py_platform_transition,
        ),
        "target_platform": attr.label(
            mandatory = True,
            doc = "Target platform to transition srcs to.",
        ),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    },
    doc = "platform_transition_filegroup that also pins rules_python's " +
          "python_version flag: a pip.parse hub selects wheels by python " +
          "version, so the platform alone is not enough.",
)

def _msis(ctx):
    """The python.org per-feature MSIs, in extraction order."""
    return [
        ctx.file.msi_ucrt,
        ctx.file.msi_core,
        ctx.file.msi_exe,
        ctx.file.msi_lib,
        ctx.file.msi_pip,
    ]

def _python_cab_impl(ctx):
    cab = ctx.actions.declare_file(ctx.label.name + ".cab")

    # Derive the name==version install request from the wheel filenames
    # (PEP 427), so it can never diverge from the fetched closure and every
    # package installs as explicitly REQUESTED, like the historic pipenv flow.
    wheel_files = ctx.files.wheels
    requirements = []
    for w in wheel_files:
        segments = w.basename.split("-")
        if len(segments) < 3 or not w.basename.endswith(".whl"):
            fail("not a wheel filename: %r" % w.basename)
        requirements.append("{}=={}".format(segments[0], segments[1]))
    requirements = sorted(requirements)

    # The venv seeds pip (the historic flow's virtualenv did, so customers can
    # `.venv\Scripts\pip install` extra plugin deps); the same pinned wheel
    # also replaces the base interpreter's ensurepip bootstrap.
    pip_pins = [r for r in requirements if r.startswith("pip==")]
    if len(pip_pins) != 1:
        fail("wheels must contain exactly one pip wheel, got %r" % requirements)

    # Production-shape 3-line pyvenv.cfg, written as a build input.
    pyvenv_cfg = ctx.actions.declare_file(ctx.label.name + ".pyvenv.cfg")
    ctx.actions.write(
        output = pyvenv_cfg,
        content = "home = {home}\nversion_info = {ver}\ninclude-system-site-packages = false\n".format(
            home = _PYVENV_HOME,
            ver = ctx.attr.python_version,
        ),
    )

    args = ctx.actions.args()
    args.add("--workdir", cab.path + ".work")
    args.add("--out", cab)
    args.add("--py-short", _python_version_short(ctx.attr.python_version))
    args.add("--py-major-minor", python_version_major_minor(ctx.attr.python_version))
    args.add("--extract-msi", ctx.executable.extract_msi)
    args.add("--msiinfo", ctx.file.msiinfo)
    args.add("--cabextract", ctx.file.cabextract)
    args.add("--libmsi", ctx.file.libmsi)
    args.add("--pip-offline", ctx.executable.pip_offline)
    args.add("--make-exe-wrappers", ctx.executable.make_exe_wrappers)
    args.add("--pack-cab", ctx.executable.pack_cab)
    args.add("--pip-requirement", pip_pins[0])
    args.add("--wrapper-shebang", _WRAPPER_SHEBANG)
    args.add("--pyvenv-cfg", pyvenv_cfg)
    args.add("--postinstall", ctx.file.postinstall_cmd)
    args.add_all(requirements, before_each = "--requirement")
    args.add_all(ctx.files.venv_scripts, before_each = "--venv-script")
    args.add_all(wheel_files, before_each = "--wheel")
    args.add_all(_msis(ctx), before_each = "--msi")

    ctx.actions.run(
        executable = ctx.attr._build_script[DefaultInfo].files_to_run,
        arguments = [args],
        outputs = [cab],
        inputs = _msis(ctx) + wheel_files + ctx.files.venv_scripts + [
            ctx.file.postinstall_cmd,
            pyvenv_cfg,
            ctx.file.msiinfo,
            ctx.file.libmsi,
            ctx.file.cabextract,
        ],
        tools = [
            ctx.attr.extract_msi[DefaultInfo].files_to_run,
            ctx.attr.pack_cab[DefaultInfo].files_to_run,
            ctx.attr.pip_offline[DefaultInfo].files_to_run,
            ctx.attr.make_exe_wrappers[DefaultInfo].files_to_run,
        ],
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
            doc = "Full CPython version (e.g. \"3.13.13\"); must match PYTHON_VERSION_WINDOWS " +
                  "in //:package_versions.bzl.",
        ),
        "venv_scripts": attr.label_list(
            allow_files = True,
            doc = "Static venv activation scripts copied into .venv/Scripts (see venv_scripts/).",
        ),
        "wheels": attr.label_list(
            allow_files = [".whl"],
            doc = "Pinned win_amd64/cp3xx wheel closure (the @windows_python_wheels " +
                  "pip.parse hub, resolved for the windows platform and the CAB's " +
                  "python version by py_platform_transition_filegroup) installed " +
                  "offline into the CAB; must include exactly one pip wheel.",
        ),
        "_build_script": attr.label(
            default = Label(":build_python_cab"),
            executable = True,
            cfg = "exec",
        ),
    },
)
