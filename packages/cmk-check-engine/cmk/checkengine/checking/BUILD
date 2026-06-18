load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "checking",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:cpu-tracking",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-check-engine:checker-plugin",
        "//packages/cmk-check-engine:helper-interface",
        "//packages/cmk-check-engine:inventory",
        "//packages/cmk-check-engine:lib",
        "//packages/cmk-check-engine:section-parser",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-check-engine:specs",
        "//packages/cmk-check-engine/cmk/checkengine/parser",
        "//packages/cmk-check-engine/cmk/checkengine/plugin_backend",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-plugin-apis:agent_based",
    ],
)
