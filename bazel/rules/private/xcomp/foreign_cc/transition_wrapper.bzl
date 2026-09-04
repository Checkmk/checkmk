"""Shared platform-transitioning wrapper rule for xcomp's foreign_cc macros."""

load("@rules_foreign_cc//foreign_cc:providers.bzl", "ForeignCcDepsInfo")
load(":private/xcomp/transition.bzl", "transition_platform", _HOST_PLATFORM = "HOST_PLATFORM")

def _platform_transitioned_foreign_cc_target_impl(ctx):
    return [
        ctx.attr.target[DefaultInfo],
        ctx.attr.target[CcInfo],
        ctx.attr.target[ForeignCcDepsInfo],
        ctx.attr.target[OutputGroupInfo],
    ]

platform_transitioned_foreign_cc_target = rule(
    implementation = _platform_transitioned_foreign_cc_target_impl,
    cfg = transition_platform,
    attrs = {
        "platform": attr.label(default = _HOST_PLATFORM),
        "target": attr.label(providers = [ForeignCcDepsInfo]),
    },
)
