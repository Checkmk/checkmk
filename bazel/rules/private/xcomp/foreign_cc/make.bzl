"""Cross-compilable make() macro with platform transition support."""

load("@rules_foreign_cc//foreign_cc:defs.bzl", _make = "make")
load(":private/xcomp/foreign_cc/transition_wrapper.bzl", "platform_transitioned_foreign_cc_target")
load(":private/xcomp/transition.bzl", _HOST_PLATFORM = "HOST_PLATFORM")

def _impl(name, platform, **kwargs):
    tags = kwargs.pop("tags", None) or []
    visibility = kwargs.pop("visibility", None)
    _make(
        name = name + "_make",
        tags = tags + ["manual"],
        visibility = ["//visibility:private"],
        **kwargs
    )
    platform_transitioned_foreign_cc_target(
        name = name,
        platform = platform,
        target = name + "_make",
        tags = tags,
        visibility = visibility,
    )

make = macro(
    implementation = _impl,
    inherit_attrs = _make,
    attrs = {"platform": attr.label(default = _HOST_PLATFORM, configurable = False)},
)
