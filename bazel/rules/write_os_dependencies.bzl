def _write_os_dependencies_impl(ctx):
    out = ctx.actions.declare_file(ctx.attr.out_name if ctx.attr.out_name else ctx.label.name + ".txt")

    ctx.actions.run(
        executable = ctx.executable._tool,
        inputs = [ctx.file.src],
        outputs = [out],
        arguments = [
            ctx.file.src.path,
            out.path,
            ctx.attr.separator,
        ],
        mnemonic = "ExtractOsPackages",
        progress_message = "Extracting OS_PACKAGES from %s" % ctx.file.src.short_path,
    )

    return DefaultInfo(files = depset([out]))

write_os_dependencies = rule(
    implementation = _write_os_dependencies_impl,
    attrs = {
        "src": attr.label(mandatory = True, allow_single_file = True),
        "separator": attr.string(mandatory = True),
        "out_name": attr.string(),
        "_tool": attr.label(
            default = Label("//bazel/tools:extract_os_packages"),
            executable = True,
            cfg = "exec",
        ),
    },
)
