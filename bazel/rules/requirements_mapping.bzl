"""Bazel rule for generating a pip package name → import name mapping."""

def _requirements_mapping_impl(ctx):
    metadata_files = []
    all_dist_info_files = []
    for target in ctx.attr.dist_infos:
        for f in target[DefaultInfo].files.to_list():
            all_dist_info_files.append(f)
            if f.path.endswith("/METADATA"):
                metadata_files.append(f)

    output = ctx.actions.declare_file("req_mapping.json")
    args = ctx.actions.args()
    args.add("--output", output)
    args.add_all(metadata_files)
    args.use_param_file("@%s", use_always = False)

    ctx.actions.run(
        executable = ctx.executable.tool,
        arguments = [args],
        inputs = all_dist_info_files,
        outputs = [output],
    )
    return [DefaultInfo(files = depset([output]))]

requirements_mapping = rule(
    implementation = _requirements_mapping_impl,
    attrs = {
        "dist_infos": attr.label_list(mandatory = True),
        "tool": attr.label(mandatory = True, executable = True, cfg = "exec"),
    },
)
