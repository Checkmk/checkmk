# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Starlark rules that build the Windows ``python-3.cab`` on Linux.

python_cab builds the agent's python-3.cab from the python-build-standalone
interpreter of PYTHON_VERSION_WINDOWS, and python_test_cab the harness Python
of the agent's pytest suites from the same interpreter.

The CAB has the same shape as the one historically produced by
``agents/modules/windows/Makefile`` on a Windows build node, but no
Wine / MSBuild / makecab.exe is involved: every tool the actions run is a
Bazel-managed input (see their py_binary and sh_binary targets in
BUILD.bazel).

Known deliberate deviations from the historic Windows-built CAB (all dead
weight):

* no ``py.exe`` / ``pyw.exe`` / ``pyshellext.dll`` in ``.venv/Scripts`` -- the
  py-launcher is not part of python-build-standalone and useless inside the
  agent's venv anyway.
* no ``_tkinter.pyd`` / ``xxlimited*.pyd`` / ``zlib1.dll`` in
  ``.venv/Scripts`` -- tkinter's stdlib package is stripped from the CAB, so
  the old copies could never import, and zlib1.dll is only Tcl's.
* no virtualenv bookkeeping files (``.gitignore``, ``CACHEDIR.TAG``,
  ``_virtualenv.py``/``.pth``, ``pip-*.virtualenv``) and no pipenv/virtualenv
  tool spill-over in the base ``Lib/site-packages``.
"""

load("//:package_versions.bzl", "PYTHON_VERSION_WINDOWS")

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

def _cab_python_transition_impl(_settings, _attr):
    return {
        "@rules_python//python/config_settings:python_version": python_version_major_minor(PYTHON_VERSION_WINDOWS),
    }

# pip_offline runs pip under the cab's major.minor, so that the metadata pip
# writes (RECORD bytecode tags, versioned script names) matches the cab's
# Python. Pinned on this edge, not by the py_binary's python_version: that would
# also pin the target itself, where the lint and mypy aspects then need
# @cmk_requirements wheels for that version, which only has the site's.
_cab_python_transition = transition(
    implementation = _cab_python_transition_impl,
    inputs = [],
    outputs = ["@rules_python//python/config_settings:python_version"],
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

def _python_files(ctx):
    """The interpreter's files: their repository root and a list of their paths.

    Fails analysis unless they are the interpreter of PYTHON_VERSION_WINDOWS.
    The build scripts copy exactly the listed files: the repository directory
    itself also holds those its BUILD file leaves out.
    """
    files = ctx.files._python_files
    roots = {f.owner.workspace_root: None for f in files}
    if len(roots) != 1:
        fail("the interpreter's files must come from one repository, got %r" % sorted(roots))
    root = roots.keys()[0]
    names = {f.path[len(root) + 1:]: None for f in files}
    py_short = python_version_major_minor(PYTHON_VERSION_WINDOWS).replace(".", "")
    for required in ["python.exe", "python{}.dll".format(py_short)]:
        if required not in names:
            fail("%s is not in %s: is it the interpreter of Python %s?" % (
                required,
                root,
                PYTHON_VERSION_WINDOWS,
            ))

    listed = ctx.actions.args()
    listed.set_param_file_format("multiline")
    listed.add_all(files)
    file_list = ctx.actions.declare_file(ctx.label.name + "_python_files.txt")
    ctx.actions.write(file_list, listed)
    return root, file_list

def _cab_args(ctx, cab, requirements, python_root, python_file_list):
    """The arguments both build scripts take."""
    args = ctx.actions.args()
    args.add("--out", cab)
    args.add("--cab-lib", ctx.file._cab_lib)
    args.add("--python-version", PYTHON_VERSION_WINDOWS)
    args.add("--python-root", python_root)
    args.add("--python-files", python_file_list)
    args.add("--pip-offline", ctx.executable._pip_offline)
    args.add("--pack-cab", ctx.executable._pack_cab)
    args.add_all(ctx.files.wheels, before_each = "--wheel")
    args.add_all(requirements, before_each = "--requirement")
    return args

def _cab_tools(ctx):
    return [
        ctx.attr._pack_cab[DefaultInfo].files_to_run,
        # A transitioned attr is a list, also for a 1:1 transition.
        ctx.attr._pip_offline[0][DefaultInfo].files_to_run,
    ]

# The attributes python_cab and python_test_cab share: the interpreter, the
# wheels and the tools that install them and pack the cab.
_CAB_ATTRS = {
    "wheels": attr.label_list(
        allow_files = [".whl"],
        cfg = _windows_wheels_transition,
        doc = "The all_whl_requirements of a pip.parse hub, the pinned " +
              "win_amd64/cp3xx wheel closure, plus any wheels built here: " +
              "installed offline. Must include exactly one pip wheel, the one " +
              "pip_offline runs.",
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
        cfg = _cab_python_transition,
    ),
    "_python_files": attr.label(
        default = Label("@python_windows_standalone//:files"),
        allow_files = True,
        doc = "The python-build-standalone interpreter of " +
              "PYTHON_VERSION_WINDOWS the cab starts from, less what no cab ships.",
    ),
}

def _python_cab_impl(ctx):
    cab = ctx.actions.declare_file(ctx.label.name + ".cab")

    # Derive the name==version install request from the wheel filenames
    # (PEP 427), so it can never diverge from the fetched closure and every
    # package installs as explicitly REQUESTED, like the historic pipenv flow.
    requirements = _wheel_requirements(ctx.files.wheels)

    # The venv seeds pip (the historic flow's virtualenv did, so customers can
    # `.venv\Scripts\pip install` extra plugin deps). The base interpreter gets
    # none, see build_python_cab.sh. pip_offline needs the wheel nonetheless.
    _pip_requirement(requirements)

    python_root, python_file_list = _python_files(ctx)
    args = _cab_args(ctx, cab, requirements, python_root, python_file_list)
    args.add("--make-exe-wrappers", ctx.executable._make_exe_wrappers)
    args.add("--postinstall", ctx.file.postinstall_cmd)
    args.add_all(ctx.files.venv_scripts, before_each = "--venv-script")

    ctx.actions.run(
        executable = ctx.attr._build_script[DefaultInfo].files_to_run,
        arguments = [args],
        outputs = [cab],
        inputs = ctx.files.wheels + ctx.files.venv_scripts + ctx.files._python_files + [ctx.file._cab_lib, python_file_list, ctx.file.postinstall_cmd],
        tools = _cab_tools(ctx) + [ctx.attr._make_exe_wrappers[DefaultInfo].files_to_run],
        mnemonic = "PythonCab",
        progress_message = "Building Windows python-3.cab on Linux (%{label})",
        use_default_shell_env = True,
        # The interpreter and wheels are fetched at the fetch phase and pip installs
        # offline (--no-index --find-links).
        execution_requirements = {"block-network": ""},
    )

    return [DefaultInfo(files = depset([cab]))]

python_cab = rule(
    implementation = _python_cab_impl,
    doc = "The agent's python-3.cab: the python-build-standalone interpreter, " +
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

    python_root, python_file_list = _python_files(ctx)
    ctx.actions.run(
        executable = ctx.attr._build_script[DefaultInfo].files_to_run,
        arguments = [_cab_args(ctx, cab, requirements, python_root, python_file_list)],
        outputs = [cab],
        inputs = ctx.files.wheels + ctx.files._python_files + [ctx.file._cab_lib, python_file_list],
        tools = _cab_tools(ctx),
        mnemonic = "PythonTestCab",
        progress_message = "Building the Windows test Python cab on Linux (%{label})",
        use_default_shell_env = True,
        execution_requirements = {"block-network": ""},
    )
    return [DefaultInfo(files = depset([cab]))]

python_test_cab = rule(
    implementation = _python_test_cab_impl,
    doc = "The Windows interpreter of python_cab (same python-build-standalone " +
          "archive of PYTHON_VERSION_WINDOWS) with a test closure in its site-packages and " +
          "the stdlib kept, unittest included (less its test suite and Tk, which no cab " +
          "ships): the harness Python of the Windows agent's pytest " +
          "suites (agents/wnx/tests), unpacked with expand.exe and called by path.",
    attrs = _CAB_ATTRS | {
        "_build_script": attr.label(
            default = Label(":build_python_test_cab"),
            executable = True,
            cfg = "exec",
        ),
    },
)
