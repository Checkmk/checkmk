load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _define_from_flag_impl(ctx):
    # Adapted from https://medium.com/codex/fun-with-flags-8c137052e245
    return CcInfo(
        compilation_context = cc_common.create_compilation_context(
            defines = depset([
                '{}="{}"'.format(
                    ctx.attr.macro,
                    ctx.attr.value[BuildSettingInfo].value,
                ),
            ]),
        ),
    )

define_from_flag = rule(
    implementation = _define_from_flag_impl,
    attrs = {
        "macro": attr.string(mandatory = True),
        "value": attr.label(mandatory = True),
    },
)
