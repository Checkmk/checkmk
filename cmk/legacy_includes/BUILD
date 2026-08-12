load("@aspect_rules_py//py:defs.bzl", "py_library")
load("//bazel/rules:doctest.bzl", "py_doc_test")

py_library(
    name = "legacy_includes",
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/editions:__pkg__",
        "//cmk/legacy_checks:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugins:lib",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":legacy_includes"],
)
