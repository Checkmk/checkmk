load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _file_from_flag_impl(ctx):
    out = ctx.actions.declare_file(ctx.attr.out)
    ctx.actions.write(
        out,
        "\n".join(ctx.attr.content) % ctx.attr.value[BuildSettingInfo].value,
    )
    return DefaultInfo(files = depset([out]))

file_from_flag = rule(
    implementation = _file_from_flag_impl,
    attrs = {
        "out": attr.string(mandatory = True),
        "content": attr.string_list(mandatory = True),
        "value": attr.label(mandatory = True),
    },
)
