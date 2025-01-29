# the copy_directory rule cannot copy filegroups or files
# which leads to "dependency checking of directories is unsound"
# issues

def _copy_to_directory_impl(ctx):
    output_dir = ctx.actions.declare_directory(ctx.attr.out_dir)

    srcs_string = ""
    for src in ctx.files.srcs:
        srcs_string += src.path
        srcs_string += " "

    ctx.actions.run_shell(
        inputs = ctx.files.srcs,
        outputs = [output_dir],
        command = "rsync -a -L " +
                  srcs_string + output_dir.path,
    )

    return [DefaultInfo(files = depset([output_dir]))]

copy_to_directory = rule(
    implementation = _copy_to_directory_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = True, mandatory = True),
        "out_dir": attr.string(mandatory = True),
    },
)
