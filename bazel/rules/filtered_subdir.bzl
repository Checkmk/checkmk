def _filtered_subdir_impl(ctx):
    output_dir = ctx.actions.declare_directory(ctx.attr.subdir)
    ctx.actions.run_shell(
        inputs = [ctx.file.src],
        outputs = [output_dir],
        command = "rsync -a -L {exclude_opts} {src_path}/ {dst_path}/".format(
            exclude_opts = "".join(["--exclude '%s' " % exclude for exclude in ctx.attr.excludes]),
            src_path = ctx.file.src.path + "/" + ctx.attr.subdir,
            dst_path = output_dir.path,
        ),
    )

    return [DefaultInfo(files = depset([output_dir]))]

filtered_subdir = rule(
    implementation = _filtered_subdir_impl,
    attrs = {
        "src": attr.label(allow_single_file = True, providers = ["files"], mandatory = True),
        "subdir": attr.string(mandatory = True),
        "excludes": attr.string_list(),
    },
)
