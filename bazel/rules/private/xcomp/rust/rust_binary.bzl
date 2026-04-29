"""Cross-compilable rust_binary rule with platform transition support."""

load("@rules_rust//rust:defs.bzl", _rust_binary = "rust_binary")
load(":private/xcomp/transition.bzl", _transition_platform = "transition_platform")

rust_binary = rule(
    implementation = lambda ctx: ctx.super(),
    parent = _rust_binary,
    cfg = _transition_platform,
    attrs = {
        "platform": attr.label(default = "@platforms//host"),
    },
)
