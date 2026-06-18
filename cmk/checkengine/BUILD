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
    deps = [],
)
