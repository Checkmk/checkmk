load(":private/xcomp/transition.bzl", _transition_platform = "transition_platform")

cc_binary = rule(
    implementation = lambda ctx: ctx.super(),
    parent = native.cc_binary,
    cfg = _transition_platform,
    attrs = {
        "platform": attr.label(default = "@platforms//host"),
    },
)
