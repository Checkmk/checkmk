load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "bandit-nosec-markers",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = ["//tests:__subpackages__"],
)
