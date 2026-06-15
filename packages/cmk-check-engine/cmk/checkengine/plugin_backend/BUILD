load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "plugin_backend",
    srcs = glob(["*.py"]),
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-check-engine:specs",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-trace",
    ],
)
