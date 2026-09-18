"""Platform transition for cross-compilation support."""

# The label Bazel itself puts into --platforms when the flag is unset: --platforms
# has an empty default and is filled in from --host_platform, whose default is
# PlatformOptions.DEFAULT_HOST_PLATFORM. That label is only an alias for
# @platforms//host, but configurations are keyed on the label *string*, not on the
# platform it resolves to. Spelling it "@platforms//host" here would therefore make
# the host case a non-identity transition, forking a second host configuration and
# rebuilding everything reachable from both a transitioned and an untransitioned
# target (@openssl, for one). Keep in sync with --host_platform's default.
HOST_PLATFORM = "@bazel_tools//tools:host_platform"

def _transition_platform_impl(settings, attr):
    return {
        "//command_line_option:compilation_mode": getattr(attr, "compilation_mode", "") or settings["//command_line_option:compilation_mode"],
        "//command_line_option:platforms": str(attr.platform),
    }

transition_platform = transition(
    implementation = _transition_platform_impl,
    inputs = ["//command_line_option:compilation_mode"],
    outputs = [
        "//command_line_option:platforms",
        "//command_line_option:compilation_mode",
    ],
)
