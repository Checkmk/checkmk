# Filegroups have by default no way to access only certain files.
# The `filter_directory` rule from `rules_pkg` only alows for excluding
# files where the whole path and name is known. See also
# https://github.com/bazelbuild/rules_pkg/issues/85
# To be able to exclude patterns or directories this rule can be used.

def _exclude_from_filegroup_impl(ctx):
    output_dir = ctx.actions.declare_directory("rest")

    exclude_string = ""
    for exclude in ctx.attr.excludes:
        exclude_string += "--exclude %s " % exclude

    ctx.actions.run_shell(
        inputs = [ctx.file.src],
        outputs = [output_dir],
        command = "rsync -a -L " +
                  exclude_string +
                  ctx.file.src.path + "/ " + output_dir.path,
    )

    return [DefaultInfo(files = depset([output_dir]))]

exclude_from_filegroup = rule(
    implementation = _exclude_from_filegroup_impl,
    attrs = {
        "src": attr.label(allow_single_file = True, providers = ["files"], mandatory = True),
        "excludes": attr.string_list(mandatory = True, allow_empty = False),
    },
)
