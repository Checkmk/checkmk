load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "common",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../../../.."],
    visibility = ["//tests/integration/plugin_consistency:__subpackages__"],
    deps = [
        "//cmk/gui/dashboard",
        "//cmk/gui/graphing",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-check-engine/cmk/checkengine/plugin_backend",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugins:all_families",
        requirement("pytest"),
    ],
)
