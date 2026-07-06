"""Rule that generates ``bin/`` console-script wrappers from a wheel's entry points.

A wheel declares its ``console_scripts`` in ``*.dist-info/entry_points.txt``. Since we unzip
wheels into ``site-packages/`` instead of installing them, nothing materialises the executable
wrappers that an installer would normally create. This rule fills that gap: it reads the wheel's
standard entry-point metadata and emits one wrapper per ``console_scripts`` entry into a
directory (``TreeArtifact``), ready to be packaged under ``bin/``.
"""

def _wheel_console_scripts_impl(ctx):
    # The rule's only output: a directory named after the target itself.
    out_dir = ctx.actions.declare_directory(ctx.attr.name)
    args = ctx.actions.args()
    args.add("--wheel", ctx.file.whl)
    args.add("--out", out_dir.path)
    ctx.actions.run(
        executable = ctx.executable._tool,
        arguments = [args],
        inputs = [ctx.file.whl],
        outputs = [out_dir],
        mnemonic = "ConsoleScripts",
        progress_message = "Generating console-script wrappers for %{label}",
    )
    return [DefaultInfo(files = depset([out_dir]))]

wheel_console_scripts = rule(
    implementation = _wheel_console_scripts_impl,
    attrs = {
        "whl": attr.label(mandatory = True, allow_single_file = True, doc = "Wheel to read entry points from."),
        "_tool": attr.label(
            default = "//bazel/rules:console_scripts_gen",
            executable = True,
            cfg = "exec",
        ),
    },
    doc = "Emits a directory of bin/ wrappers for a wheel's console_scripts entry points.",
)
