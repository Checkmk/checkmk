load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "parser",
    srcs = glob(["*.py"]),
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//cmk/piggyback:backend",
        "//cmk/utils",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:translations",
        "//packages/cmk-check-engine:helper-interface",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
    ],
)
