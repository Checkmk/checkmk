load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "rrd",
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "@rrdtool_native//:rrdtool_python_lib",
    ],
)
