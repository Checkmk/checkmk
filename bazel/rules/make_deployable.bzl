"""Rules to prepare binaries for deployment by replacing strings."""

load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _string_replace_impl(ctx):
    output_dir = ctx.actions.declare_directory(ctx.label.name)
    value = ctx.attr.value
    for string, label in ctx.attr.replace_labels.items():
        value = value.replace("{%s}" % string, label[BuildSettingInfo].value)

    ctx.actions.run_shell(
        inputs = [ctx.file.src],
        outputs = [output_dir],
        command = """
        cp -a --dereference {src_path}/. {dst_path}
        find {dst_path} -type f {filepattern} -exec sed -i 's|{replace_pattern}|{value}|' {{}} \\;
        """.format(
            src_path = ctx.file.src.path,
            dst_path = output_dir.path,
            filepattern = "".join(["-iname %s " % pattern for pattern in ctx.attr.filepattern]),
            replace_pattern = ctx.attr.replace_pattern,
            value = value,
        ),
    )

    return [DefaultInfo(files = depset([output_dir]))]

string_replace = rule(
    implementation = _string_replace_impl,
    attrs = {
        "filepattern": attr.string_list(),
        "replace_labels": attr.string_keyed_label_dict(mandatory = True),
        "replace_pattern": attr.string(),
        "src": attr.label(allow_single_file = True, providers = ["files"], mandatory = True),
        "strip_prefix": attr.string(default = "", mandatory = False),
        "value": attr.string(),
    },
)
