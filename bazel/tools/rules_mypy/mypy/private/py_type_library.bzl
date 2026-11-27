# Modified by Checkmk GmbH, see bazel/tools/rules_mypy/VENDORED.md
"Convert pip typings packages for use with mypy."

PyTypeLibraryInfo = provider(
    doc = "Information about the content of a py_type_library.",
    fields = {
        "directory": "Directory containing site-packages.",
    },
)

def _py_type_library_impl(ctx):
    directory = ctx.actions.declare_directory(ctx.attr.name)

    args = ctx.actions.args()
    args.add("--input-dir", ctx.attr.typing.label.workspace_root)
    args.add("--output-dir", directory.path)

    ctx.actions.run(
        mnemonic = "BuildPyTypeLibrary",
        inputs = depset(transitive = [ctx.attr.typing.default_runfiles.files]),
        outputs = [directory],
        executable = ctx.executable._exec,
        arguments = [args],
        env = ctx.configuration.default_shell_env,
    )

    return [
        DefaultInfo(
            files = depset([directory]),
            runfiles = ctx.runfiles(files = [directory]),
        ),
        PyTypeLibraryInfo(
            directory = directory,
        ),
    ]

py_type_library = rule(
    implementation = _py_type_library_impl,
    attrs = {
        "typing": attr.label(),
        "_exec": attr.label(cfg = "exec", default = "//bazel/tools/rules_mypy/mypy/private:py_type_library", executable = True),
    },
)
