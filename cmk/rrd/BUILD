load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "rrd",
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:version-info",
        "//packages/cmk-crash:crash",
        "@rrdtool//:rrdtool_python_lib",
    ],
)
