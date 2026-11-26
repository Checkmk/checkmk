"""Bytecode of the Python toolchain's standard library, for the runfiles of Python tools

A py_binary of rules_python, or a wrapper around one, imports the standard library from the
toolchain's files in its runfiles, apart from the few modules Python needs before rules_python's
site setup. They hold no bytecode, so each run compiles every module of the standard library it
imports. Add a target of this rule to the data of such a binary: its runfiles put the bytecode into
the __pycache__ directories next to these sources, where Python looks for it. Binaries and tests of
aspect_rules_py, e.g. py_cmk_test, import the standard library from the toolchain's own directory
instead, so the bytecode doesn't help them.

Unchecked hash-based .pyc files depend neither on the sources' modification times, which Bazel
doesn't guarantee, nor on reading the sources on each run; the regression test checks that they
match their sources. The Python of the execution platform compiles them, from rules_python's exec
tools toolchain. Without a standard library in lib/pythonX.Y, e.g. for a Python of the system, on
Windows or for a free-threaded Python (lib/pythonX.Yt), or without an exec Python of the same
kind, the rule gives no bytecode.
"""

_PY_TOOLCHAIN = Label("@rules_python//python:toolchain_type")
_PY_EXEC_TOOLS_TOOLCHAIN = Label("@rules_python//python:exec_tools_toolchain_type")

def _version(runtime):
    info = getattr(runtime, "interpreter_version_info", None)
    return (info.major, info.minor) if info else None

def _py_stdlib_bytecode_impl(ctx):
    runtime = ctx.toolchains[_PY_TOOLCHAIN].py3_runtime
    exec_tools = ctx.toolchains[_PY_EXEC_TOOLS_TOOLCHAIN]
    exec_runtime = getattr(exec_tools.exec_tools, "exec_runtime", None) if exec_tools else None
    pyc_tag = getattr(runtime, "pyc_tag", None)
    version = _version(runtime)
    if (runtime == None or exec_runtime == None or exec_runtime.interpreter == None or
        not pyc_tag or not version or _version(exec_runtime) != version or
        getattr(exec_runtime, "pyc_tag", None) != pyc_tag):
        return [DefaultInfo()]  # e.g. a Python of the system, or no exec Python of its version
    lib = "lib/python{}.{}/".format(*version)
    sources = []
    pycs = []
    root_symlinks = {}
    args = ctx.actions.args()
    for src in runtime.files.to_list():
        if src.extension != "py" or not src.short_path.startswith("../"):
            continue
        repo, _, path = src.short_path[len("../"):].partition("/")
        if not path.startswith(lib) or "/site-packages/" in path:
            continue
        directory, _, basename = path.rpartition("/")
        runfiles_path = "{}/{}/__pycache__/{}.{}.pyc".format(
            repo,
            directory,
            basename[:-len(".py")],
            pyc_tag,
        )
        pyc = ctx.actions.declare_file("{}/{}".format(ctx.label.name, runfiles_path))
        args.add(src)
        args.add(pyc)
        sources.append(src)
        pycs.append(pyc)
        root_symlinks[runfiles_path] = pyc
    if not pycs:
        return [DefaultInfo()]  # no standard library in lib/pythonX.Y, e.g. on Windows
    args.use_param_file("%s", use_always = True)
    args.set_param_file_format("multiline")
    ctx.actions.run(
        executable = exec_runtime.interpreter,
        arguments = ["-I", "-B", ctx.file._compiler.path, args],
        inputs = depset([ctx.file._compiler] + sources, transitive = [exec_runtime.files]),
        outputs = pycs,
        mnemonic = "PyCompileStdlib",
        progress_message = "Compiling the bytecode of Python's standard library for %{label}",
        toolchain = _PY_EXEC_TOOLS_TOOLCHAIN,
    )

    # Not in DefaultInfo.files: py_binary puts the files of its data into the runfiles, too, so
    # each .pyc would be there twice. For a look at them: bazel build --output_groups=bytecode
    return [
        DefaultInfo(runfiles = ctx.runfiles(root_symlinks = root_symlinks)),
        OutputGroupInfo(bytecode = depset(pycs)),
    ]

py_stdlib_bytecode = rule(
    implementation = _py_stdlib_bytecode_impl,
    doc = "The bytecode of the toolchain's standard library, as runfiles next to its sources",
    attrs = {
        "_compiler": attr.label(
            default = Label("//bazel/rules:py_compile_bytecode.py"),
            allow_single_file = True,
        ),
    },
    toolchains = [
        _PY_TOOLCHAIN,
        config_common.toolchain_type(_PY_EXEC_TOOLS_TOOLCHAIN, mandatory = False),
    ],
)
