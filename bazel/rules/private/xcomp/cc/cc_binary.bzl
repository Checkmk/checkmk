"""Cross-compilable cc_binary rule with platform transition support."""

load(":private/xcomp/transition.bzl", _transition_platform = "transition_platform")

_cc_binary_transitioned = rule(
    implementation = lambda ctx: ctx.super(),
    parent = native.cc_binary,
    cfg = _transition_platform,
    attrs = {
        "compilation_mode": attr.string(
            doc = "Pin a compilation mode (e.g. 'opt'); empty inherits the command line.",
            default = "",
        ),
        "platform": attr.label(default = "@platforms//host"),
    },
)

def cc_binary(name, opt = False, strip = False, features = [], **kwargs):
    """cc_binary with optional opt/strip wired to the //bazel/cmk flags.

    Args:
        name: target name.
        opt: when True, build in 'opt' mode if //bazel/cmk/optimize is enabled.
        strip: when True, strip symbols if //bazel/cmk/strip is enabled.
        features: extra toolchain features.
        **kwargs: forwarded to the underlying rule.
    """
    _cc_binary_transitioned(
        name = name,
        compilation_mode = select({
            "@cmk//optimize:enabled": "opt",
            "//conditions:default": "",
        }) if opt else "",
        features = features + (select({
            "@cmk//strip:enabled": ["strip_all_symbols"],
            "//conditions:default": [],
        }) if strip else []),
        **kwargs
    )
