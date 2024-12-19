load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _binreplace_version_from_flag_impl(ctx):
    tmp_out = ctx.actions.declare_file(ctx.attr.intermediate_out)
    ctx.actions.run(
        outputs = [tmp_out],
        inputs = [ctx.file.src],
        tools = ctx.files.tool,
        executable = ctx.executable.tool,
        arguments = [
            "--regular-expression",
            ctx.attr.reg_ex,
            ctx.attr.new_value.format(version = ctx.attr.value[BuildSettingInfo].value),
            ctx.file.src.path,
        ],
    )

    # This is necessary to destinguish between the editions.
    # If binreplace could handle output names for files,
    # this could be removed
    ctx.actions.run(
        outputs = [ctx.outputs.out],
        inputs = [tmp_out],
        executable = "cp",
        arguments = [
            tmp_out.path,
            ctx.outputs.out.path,
        ],
    )

binreplace_version_from_flag = rule(
    implementation = _binreplace_version_from_flag_impl,
    attrs = {
        "src": attr.label(mandatory = True, allow_single_file = True),
        "out": attr.output(mandatory = True),
        "intermediate_out": attr.string(mandatory = True),
        "reg_ex": attr.string(mandatory = True),
        "new_value": attr.string(mandatory = True),
        "tool": attr.label(
            mandatory = True,
            cfg = "exec",
            allow_files = True,
            executable = True,
        ),
        "value": attr.label(mandatory = True),
    },
)
