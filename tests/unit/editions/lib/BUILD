load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "lib",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-ruleset-matcher",
    ],
)
