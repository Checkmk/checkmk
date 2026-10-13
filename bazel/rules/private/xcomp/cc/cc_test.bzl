"""Cross-compilable cc_test rule with platform transition support."""

load(":private/xcomp/transition.bzl", _HOST_PLATFORM = "HOST_PLATFORM", _transition_platform = "transition_platform")

cc_test = rule(
    implementation = lambda ctx: ctx.super(),
    cfg = _transition_platform,
    parent = native.cc_test,
    attrs = {
        "platform": attr.label(default = _HOST_PLATFORM),
    },
)
