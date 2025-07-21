load(":private/xcomp/transition.bzl", _transition_platform = "transition_platform")

cc_library = rule(
    implementation = lambda ctx: ctx.super(),
    cfg = _transition_platform,
    parent = native.cc_library,
    attrs = {
        "platform": attr.label(
            default = "//bazel/platforms:x86_64-linux-gcc-hermetic",
        ),
    },
)
