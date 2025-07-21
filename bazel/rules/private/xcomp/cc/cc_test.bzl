load(":private/xcomp/transition.bzl", _transition_platform = "transition_platform")

cc_test = rule(
    implementation = lambda ctx: ctx.super(),
    cfg = _transition_platform,
    parent = native.cc_test,
    attrs = {
        "platform": attr.label(default = "@platforms//host"),
    },
)
