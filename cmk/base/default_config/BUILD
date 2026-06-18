load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "default-config",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        "//cmk/inventory",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-check-engine:specs",
        "//packages/cmk-check-engine/cmk/checkengine/discovery",
    ],
)
