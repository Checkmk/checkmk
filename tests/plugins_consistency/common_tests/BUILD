load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "common_tests",
    srcs = glob(["**/*.py"]),
    visibility = ["//tests/plugins_consistency:__subpackages__"],
    deps = [
        "//cmk/checkengine",
        "//cmk/editions:community",
        "//tests/code_quality:bazel_utils",
        requirement("pytest"),
    ],
)
