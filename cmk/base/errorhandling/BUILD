load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "errorhandling",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        "//cmk/checkengine",
        "//cmk/piggyback:backend",
        "//cmk/utils",
        "//packages/cmk-ccc:crash-reporting",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:helper-interface",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-check-engine:specs",
    ],
)
