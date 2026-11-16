load("@aspect_rules_py//py:defs.bzl", "py_library")
load("//bazel/rules:doctest.bzl", "py_doc_test")

py_library(
    name = "agents",
    srcs = ["mk_filestats.py"],
    # Only tests use the agent plug-ins as Python code, see //cmk/plugins:plugins.
    visibility = ["//tests:__subpackages__"],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":agents"],
)

filegroup(
    name = "files",
    srcs = glob(
        ["*"],
        exclude = ["BUILD"],
    ),
    visibility = ["//cmk/plugins:__pkg__"],
)
