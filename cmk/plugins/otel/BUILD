load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "otel",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    target_compatible_with = select({
        "@//:gpl+nonfree_repo": [],
        "@//:gpl_repo": ["@platforms//:incompatible"],
    }),
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-telemetry:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/nonfree/ultimate",
        "//non-free/packages/cmk-metric-backend",
        "//non-free/packages/cmk-metric-backend:cmk-metric-backend-fetcher",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:rulesets",
        requirement("opentelemetry-proto"),
        requirement("protobuf"),
    ],
)
