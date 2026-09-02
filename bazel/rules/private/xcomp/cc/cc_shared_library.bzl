"""Cross-compilable cc_shared_library rule with platform transition support."""

load(":private/xcomp/transition.bzl", _transition_platform = "transition_platform")

cc_shared_library = rule(
    implementation = lambda ctx: ctx.super(),
    cfg = _transition_platform,
    parent = native.cc_shared_library,
    attrs = {
        "platform": attr.label(default = "@platforms//host"),
    },
)
