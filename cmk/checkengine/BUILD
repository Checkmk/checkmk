load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "checkengine",
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//doc/documentation:__subpackages__",
        "//non-free/packages/cmk-core-helpers:__subpackages__",
        "//non-free/packages/cmk-robotmk:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/inventory",
        "//cmk/piggyback:backend",
        "//cmk/utils",
        "//packages/cmk-ccc:cpu-tracking",
        "//packages/cmk-ccc:timeout",
        "//packages/cmk-ccc:translations",
        "//packages/cmk-check-engine:checker-plugin",
        "//packages/cmk-check-engine:fetcher-protocol",
        "//packages/cmk-check-engine:helper-interface",
        "//packages/cmk-check-engine:lib",
        "//packages/cmk-check-engine:section-parser",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-check-engine:specs",
        "//packages/cmk-check-engine/cmk/checkengine/parser",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-trace",
    ],
)
