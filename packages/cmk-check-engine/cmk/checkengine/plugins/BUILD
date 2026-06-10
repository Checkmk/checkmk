load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "plugins",
    srcs = glob(["*.py"]),
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-check-engine:specs",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:discover_plugins",
    ],
)
