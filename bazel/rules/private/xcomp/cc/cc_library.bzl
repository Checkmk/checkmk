"""Cross-compilable cc_library rule with platform transition support."""

load(":private/xcomp/transition.bzl", _HOST_PLATFORM = "HOST_PLATFORM", _transition_platform = "transition_platform")

cc_library = rule(
    implementation = lambda ctx: ctx.super(),
    cfg = _transition_platform,
    parent = native.cc_library,
    attrs = {
        "platform": attr.label(default = _HOST_PLATFORM),
    },
)
