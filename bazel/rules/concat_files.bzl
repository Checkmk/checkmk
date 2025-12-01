def _concat_files_impl(ctx):
    out = ctx.actions.declare_file(ctx.attr.name)
    ctx.actions.run_shell(
        inputs = ctx.files.srcs,
        outputs = [out],
        command = "awk '{{print}}' {} > {}".format(" ".join([f.path for f in ctx.files.srcs]), out.path),
    )
    return [DefaultInfo(files = depset([out]))]

concat_files = rule(
    doc = "Concatenate given files into a single output file.",
    implementation = _concat_files_impl,
    attrs = {
        "srcs": attr.label_list(
            mandatory = True,
            allow_files = True,
            doc = "List of files to concatenate",
        ),
    },
)
