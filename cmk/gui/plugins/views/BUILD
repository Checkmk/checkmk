load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "views",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)
