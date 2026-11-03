load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "config",
    srcs = glob(["*.py"]),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)
