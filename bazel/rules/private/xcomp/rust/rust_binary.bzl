"""Cross-compilable rust_binary rule with platform transition support."""

load("@rules_rust//rust:defs.bzl", _rust_binary = "rust_binary")
load(":private/xcomp/transition.bzl", _transition_platform = "transition_platform")

_rust_binary_transitioned = rule(
    implementation = lambda ctx: ctx.super(),
    parent = _rust_binary,
    cfg = _transition_platform,
    attrs = {
        "compilation_mode": attr.string(
            doc = "Pin a compilation mode (e.g. 'opt'); empty inherits the command line.",
            default = "",
        ),
        "platform": attr.label(default = "@platforms//host"),
    },
)

def rust_binary(name, opt = False, strip = False, rustc_flags = [], **kwargs):
    """rust_binary with optional opt/strip wired to the //bazel/cmk flags.

    Args:
        name: target name.
        opt: when True, build in 'opt' mode if //bazel/cmk/optimize is enabled.
        strip: when True, strip symbols if //bazel/cmk/strip is enabled.
        rustc_flags: extra rustc flags (strip flags are appended when strip=True).
        **kwargs: forwarded to the underlying rule.
    """
    _rust_binary_transitioned(
        name = name,
        compilation_mode = select({
            "@cmk//optimize:enabled": "opt",
            "//conditions:default": "",
        }) if opt else "",
        rustc_flags = rustc_flags + (select({
            "@cmk//strip:enabled": ["-Cstrip=symbols"],
            "//conditions:default": [],
        }) if strip else []),
        **kwargs
    )
