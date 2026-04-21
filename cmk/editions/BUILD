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
        "//cmk/post_rename_site",
        "//cmk/post_rename_site:internal",
        "//cmk/post_rename_site/plugins",
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
