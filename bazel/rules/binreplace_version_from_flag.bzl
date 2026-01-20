load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _binreplace_version_from_flag_impl(ctx):
    replacement = ctx.attr.template.format(
        **{key: label[BuildSettingInfo].value for key, label in ctx.attr.replace_labels.items()}
    )
    ctx.actions.run(
        outputs = [ctx.outputs.out],
        inputs = [ctx.file.src],
        tools = ctx.files.tool,
        executable = ctx.executable.tool,
        arguments = [
            "--regular-expression",
            ctx.attr.reg_ex,
            replacement,
            ctx.file.src.path,
        ],
    )

binreplace_version_from_flag = rule(
    implementation = _binreplace_version_from_flag_impl,
    attrs = {
        "src": attr.label(mandatory = True, allow_single_file = True),
        "out": attr.output(mandatory = True),
        "replace_labels": attr.string_keyed_label_dict(
            mandatory = True,
            allow_empty = False,
            doc = "Maps the key from the template to the desired value",
        ),
        "reg_ex": attr.string(mandatory = True),
        "template": attr.string(mandatory = True),
        "tool": attr.label(
            mandatory = True,
            cfg = "exec",
            allow_files = True,
            executable = True,
        ),
    },
)
