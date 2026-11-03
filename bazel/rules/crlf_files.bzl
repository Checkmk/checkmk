"""crlf_files(): copies of files with the CRLF line ends Windows needs."""

def _crlf_files_impl(ctx):
    suffixes = tuple(ctx.attr.suffixes)
    outputs = []
    sources = []
    converted = []
    args = ctx.actions.args()
    for src in ctx.files.srcs:
        output = ctx.actions.declare_file(ctx.label.name + "/" + src.short_path)
        outputs.append(output)
        if src.basename.endswith(suffixes):
            sources.append(src)
            converted.append(output)
            args.add(src)
            args.add(output)
        else:
            ctx.actions.symlink(output = output, target_file = src)
    if converted:
        ctx.actions.run(
            executable = ctx.executable._crlf,
            arguments = [args],
            inputs = sources,
            outputs = converted,
            mnemonic = "Crlf",
            progress_message = "Converting line ends of %{label}",
        )
    return [DefaultInfo(files = depset(outputs))]

crlf_files = rule(
    doc = """The srcs under <name>/<their repository path>, the ones ending in one of
suffixes with CRLF line ends (cmd.exe and the tests comparing sizes need them;
a Linux checkout has LF), the others as they are. A pkg_files() with
strip_prefix = strip_prefix.from_pkg("<name>") maps them back to their
repository paths.""",
    implementation = _crlf_files_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = True, mandatory = True),
        "suffixes": attr.string_list(mandatory = True),
        "_crlf": attr.label(
            default = Label("//bazel/rules:crlf_files"),
            executable = True,
            cfg = "exec",
        ),
    },
)
