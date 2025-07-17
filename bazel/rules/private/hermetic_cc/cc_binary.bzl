# See design doc in https://github.com/bazelbuild/bazel/issues/19507
# regarding rule extensions.

load(
    ":private/hermetic_cc/transition.bzl",
    "HERMETIC_PLATFORM",
    _transition_platform = "transition_platform",
)

cc_binary = rule(
    implementation = lambda ctx: ctx.super(),
    parent = native.cc_binary,
    cfg = _transition_platform,
    attrs = {
        "platform": attr.label(default = HERMETIC_PLATFORM),
    },
)
