"""Cross-compilable configure_make() macro with platform transition support."""

load("@rules_foreign_cc//foreign_cc:defs.bzl", _configure_make = "configure_make")
load(":private/xcomp/foreign_cc/transition_wrapper.bzl", "platform_transitioned_foreign_cc_target")
load(":private/xcomp/transition.bzl", _HOST_PLATFORM = "HOST_PLATFORM")

def _impl(name, platform, **kwargs):
    tags = kwargs.pop("tags", None) or []
    visibility = kwargs.pop("visibility", None)
    _configure_make(
        name = name + "_configure_make",
        tags = tags + ["manual"],
        visibility = ["//visibility:private"],
        **kwargs
    )
    platform_transitioned_foreign_cc_target(
        name = name,
        platform = platform,
        target = name + "_configure_make",
        tags = tags,
        visibility = visibility,
    )

configure_make = macro(
    implementation = _impl,
    inherit_attrs = _configure_make,
    attrs = {"platform": attr.label(default = _HOST_PLATFORM, configurable = False)},
)
