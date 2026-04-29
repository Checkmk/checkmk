"""Cross-compilable rust_test rule with platform transition support."""

load("@rules_rust//rust:defs.bzl", _rust_test = "rust_test")
load(":private/xcomp/transition.bzl", _transition_platform = "transition_platform")

rust_test = rule(
    implementation = lambda ctx: ctx.super(),
    parent = _rust_test,
    cfg = _transition_platform,
    attrs = {
        "platform": attr.label(default = "@platforms//host"),
    },
)
