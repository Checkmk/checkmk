# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Starlark rules that build the Windows ``python-3.cab`` on Linux.

python_msi_tree extracts the python.org MSIs once; python_cab builds the
agent's python-3.cab from that tree, and python_test_cab the harness Python
of the agent's pytest suites.

The CAB has the same shape as the one historically produced by
``agents/modules/windows/Makefile`` on a Windows build node, but no
Wine / MSBuild / makecab.exe is involved: every tool the actions run is a
Bazel-managed input (see their py_binary and sh_binary targets in
BUILD.bazel).

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

load("//:package_versions.bzl", "PYTHON_VERSION_WINDOWS")
load(":python_msis.bzl", "PYTHON_MSI_FEATURES")

def python_version_major_minor(version):
    # "3.13.14" -> "3.13", the part the cp3xx wheel ABI tag encodes
    parts = version.split(".")
    if len(parts) < 2:
        fail("python_version must be a dotted version like 3.13.13, got %r" % version)
    return parts[0] + "." + parts[1]

def _windows_wheels_transition_impl(_settings, _attr):
    return {
        "//command_line_option:platforms": str(Label("//bazel/platforms:x86_64-windows")),
        "@rules_python//python/config_settings:python_version": python_version_major_minor(PYTHON_VERSION_WINDOWS),
    }

# A pip.parse hub selects wheels by platform and python version: build the
# wheels attrs for Windows and the cab's major.minor.
_windows_wheels_transition = transition(
    implementation = _windows_wheels_transition_impl,
    inputs = [],
    outputs = [
        "//command_line_option:platforms",
        "@rules_python//python/config_settings:python_version",
    ],
)

def _python_msi_tree_impl(ctx):
    tree = ctx.actions.declare_directory(ctx.label.name)
    py_short = python_version_major_minor(PYTHON_VERSION_WINDOWS).replace(".", "")

    args = ctx.actions.args()
    args.add("--msiinfo", ctx.executable._msiinfo)
    args.add("--cabextract", ctx.file._cabextract)
    args.add("--directory", tree.path)
    args.add("--require", "python.exe")
    args.add("--require", "python{}.dll".format(py_short))
    args.add_all(ctx.files.msis)

    ctx.actions.run(
        executable = ctx.executable._extract_msi,
        arguments = [args],
        outputs = [tree],
        inputs = ctx.files.msis,
        tools = [ctx.attr._msiinfo[DefaultInfo].files_to_run, ctx.file._cabextract],
        mnemonic = "PythonMsiExtract",
        progress_message = "Extracting the python.org MSIs (%{label})",
        execution_requirements = {"block-network": ""},
    )
    return [DefaultInfo(files = depset([tree]))]

python_msi_tree = rule(
    implementation = _python_msi_tree_impl,
    doc = "The python.org MSIs of PYTHON_VERSION_WINDOWS extracted into the " +
          "install-root tree, the interpreter python_cab and python_test_cab " +
          "start from.",
    attrs = {
        "msis": attr.label_list(
            default = ["@python_msi_{}//file".format(f) for f in PYTHON_MSI_FEATURES],
            allow_files = [".msi"],
            doc = "The python.org per-feature MSIs, in extraction order.",
        ),
        "_cabextract": attr.label(
            default = Label(":_cabextract"),
            allow_single_file = True,
            cfg = "exec",
        ),
        "_extract_msi": attr.label(
            default = Label(":extract_msi"),
            executable = True,
            cfg = "exec",
        ),
        # Finds libmsi through its RUNPATH.
        "_msiinfo": attr.label(
            default = Label("@msitools//:msiinfo"),
            executable = True,
            cfg = "exec",
        ),
    },
)

def _wheel_requirements(wheel_files):
    """The name==version request for each wheel, from its filename (PEP 427)."""
    requirements = []
    for w in wheel_files:
        segments = w.basename.split("-")
        if len(segments) < 3 or not w.basename.endswith(".whl"):
            fail("not a wheel filename: %r" % w.basename)
        requirements.append("{}=={}".format(segments[0], segments[1]))
    return sorted(requirements)

def _pip_requirement(requirements):
    """The closure's one pip pin: pip_offline runs pip from that wheel."""
    pip_pins = [r for r in requirements if r.startswith("pip==")]
    if len(pip_pins) != 1:
        fail("wheels must contain exactly one pip wheel, got %r" % requirements)
    return pip_pins[0]

def _cab_args(ctx, cab, requirements):
    """The arguments both build scripts take."""
    args = ctx.actions.args()
    args.add("--out", cab)
    args.add("--cab-lib", ctx.file._cab_lib)
    args.add("--python-version", PYTHON_VERSION_WINDOWS)
    args.add("--python-tree", ctx.file.python_tree.path)
    args.add("--pip-offline", ctx.executable._pip_offline)
    args.add("--pack-cab", ctx.executable._pack_cab)
    args.add_all(ctx.files.wheels, before_each = "--wheel")
    args.add_all(requirements, before_each = "--requirement")
    return args

def _cab_tools(ctx):
    return [
        ctx.attr._pack_cab[DefaultInfo].files_to_run,
        ctx.attr._pip_offline[DefaultInfo].files_to_run,
    ]

# The attributes python_cab and python_test_cab share: the extracted
# interpreter, the wheels and the tools that install them and pack the cab.
_CAB_ATTRS = {
    "python_tree": attr.label(
        mandatory = True,
        allow_single_file = True,
        doc = "The python_msi_tree the cab starts from.",
    ),
    "wheels": attr.label_list(
        allow_files = [".whl"],
        cfg = _windows_wheels_transition,
        doc = "The all_whl_requirements of a pip.parse hub: the pinned " +
              "win_amd64/cp3xx wheel closure, installed offline. Must include " +
              "exactly one pip wheel, the one pip_offline runs.",
    ),
    "_cab_lib": attr.label(
        default = Label(":cab_lib"),
        allow_single_file = True,
    ),
    "_pack_cab": attr.label(
        default = Label(":pack_cab"),
        executable = True,
        cfg = "exec",
    ),
    "_pip_offline": attr.label(
        default = Label(":pip_offline"),
        executable = True,
        cfg = "exec",
    ),
}

def _python_cab_impl(ctx):
    cab = ctx.actions.declare_file(ctx.label.name + ".cab")

    # Derive the name==version install request from the wheel filenames
    # (PEP 427), so it can never diverge from the fetched closure and every
    # package installs as explicitly REQUESTED, like the historic pipenv flow.
    requirements = _wheel_requirements(ctx.files.wheels)

    # The venv seeds pip (the historic flow's virtualenv did, so customers can
    # `.venv\Scripts\pip install` extra plugin deps); the same pinned wheel
    # also replaces the base interpreter's ensurepip bootstrap.
    pip_requirement = _pip_requirement(requirements)

    args = _cab_args(ctx, cab, requirements)
    args.add("--make-exe-wrappers", ctx.executable._make_exe_wrappers)
    args.add("--pip-requirement", pip_requirement)
    args.add("--postinstall", ctx.file.postinstall_cmd)
    args.add_all(ctx.files.venv_scripts, before_each = "--venv-script")

    ctx.actions.run(
        executable = ctx.attr._build_script[DefaultInfo].files_to_run,
        arguments = [args],
        outputs = [cab],
        inputs = ctx.files.wheels + ctx.files.venv_scripts + [ctx.file._cab_lib, ctx.file.python_tree, ctx.file.postinstall_cmd],
        tools = _cab_tools(ctx) + [ctx.attr._make_exe_wrappers[DefaultInfo].files_to_run],
        mnemonic = "PythonCab",
        progress_message = "Building Windows python-3.cab on Linux (%{label})",
        use_default_shell_env = True,
        # MSIs and wheels are fetched at the fetch phase and pip installs
        # offline (--no-index --find-links).
        execution_requirements = {"block-network": ""},
    )

    return [DefaultInfo(files = depset([cab]))]

python_cab = rule(
    implementation = _python_cab_impl,
    doc = "The agent's python-3.cab: the interpreter of a python_msi_tree, " +
          "stripped like production's, with a venv holding the wheel closure.",
    attrs = _CAB_ATTRS | {
        "postinstall_cmd": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "Agent's postinstall.cmd, copied verbatim to the install root.",
        ),
        "venv_scripts": attr.label_list(
            allow_files = True,
            doc = "Static venv activation scripts copied into .venv/Scripts (see venv_scripts/).",
        ),
        "_build_script": attr.label(
            default = Label(":build_python_cab"),
            executable = True,
            cfg = "exec",
        ),
        "_make_exe_wrappers": attr.label(
            default = Label(":make_exe_wrappers"),
            executable = True,
            cfg = "exec",
        ),
    },
)

def _python_test_cab_impl(ctx):
    cab = ctx.actions.declare_file(ctx.label.name + ".cab")
    requirements = _wheel_requirements(ctx.files.wheels)

    # Only checks there is one: pip_offline runs pip from that wheel.
    _pip_requirement(requirements)

    ctx.actions.run(
        executable = ctx.attr._build_script[DefaultInfo].files_to_run,
        arguments = [_cab_args(ctx, cab, requirements)],
        outputs = [cab],
        inputs = ctx.files.wheels + [ctx.file._cab_lib, ctx.file.python_tree],
        tools = _cab_tools(ctx),
        mnemonic = "PythonTestCab",
        progress_message = "Building the Windows test Python cab on Linux (%{label})",
        use_default_shell_env = True,
        execution_requirements = {"block-network": ""},
    )
    return [DefaultInfo(files = depset([cab]))]

python_test_cab = rule(
    implementation = _python_test_cab_impl,
    doc = "The Windows interpreter of python_cab (same python.org MSIs, same " +
          "PYTHON_VERSION_WINDOWS) with a test closure in its site-packages and " +
          "the stdlib kept: the harness Python of the Windows agent's pytest " +
          "suites (agents/wnx/tests), unpacked with expand.exe and called by path.",
    attrs = _CAB_ATTRS | {
        "_build_script": attr.label(
            default = Label(":build_python_test_cab"),
            executable = True,
            cfg = "exec",
        ),
    },
)
