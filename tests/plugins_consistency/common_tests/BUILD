load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "common_tests",
    testonly = True,
    srcs = glob(["**/*.py"]),
    visibility = ["//tests/plugins_consistency:__subpackages__"],
    deps = [
        "//cmk/gui/dashboard",
        "//cmk/gui/graphing",
        "//cmk/plugins",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine/cmk/checkengine/plugin_backend",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugins:all_families",
        "//tests/code_quality:bazel_utils",
        requirement("pytest"),
    ],
)
