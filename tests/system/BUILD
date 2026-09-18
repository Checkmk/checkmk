load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "pkg_marker",
    testonly = True,
    srcs = ["__init__.py"],
    imports = ["../.."],
    visibility = ["//tests:__subpackages__"],
)
