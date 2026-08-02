load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [":__subpackages__"],
    deps = [
        "//cmk/base/config",  # hidden in a local import
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "test_section_host_label_doc_community",
    srcs = ["test_section_host_label_doc_community.py"],
    data = [
        "//cmk/plugins:checkman",
        "//cmk/plugins:libexec",
        "//packages/cmk-plugins:checkman_all",
        "//packages/cmk-plugins:libexec_all",
    ],
    tags = [
        "deballast-keep=//cmk/plugins:plugins",  # loaded at runtime by the test (plugin discovery via conftest)
    ],
    deps = [
        ":conftest",
        "//:pyproject-toml",
        "//cmk/plugins",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-plugins:all_families",
    ],
)
