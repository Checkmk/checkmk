load("@aspect_rules_py//py:defs.bzl", "py_library")
load("//bazel/rules:doctest.bzl", "py_doc_test")

py_library(
    name = "community",
    srcs = [],
    data = [
        "//cmk/plugins:checkman_community",
        "//cmk/plugins:libexec",
        "//packages/cmk-plugins:checkman_all",
        "//packages/cmk-plugins:libexec_all",
    ],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk",
        "//packages/cmk-plugins:all_families",
    ],
)

py_doc_test(
    name = "doctest",
    srcs = [
        ":community",
    ],
    env = {
        "PYTHONWARNINGS": "ignore",
    },
    tags = [
        "doctest",
        "no-mypy",
    ],
)
