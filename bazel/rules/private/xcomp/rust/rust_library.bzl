"""Cross-compilable rust_library rule with platform transition support."""

load("@rules_rust//rust:defs.bzl", _rust_library = "rust_library")
load(":private/xcomp/transition.bzl", _transition_platform = "transition_platform")

rust_library = rule(
    implementation = lambda ctx: ctx.super(),
    parent = _rust_library,
    cfg = _transition_platform,
    attrs = {
        "platform": attr.label(default = "@platforms//host"),
    },
)
