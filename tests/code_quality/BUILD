load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "bazel_utils",
    srcs = ["bazel_utils.py"],
    imports = ["../.."],
    visibility = ["//:__subpackages__"],
)

py_library(
    name = "code_quality",
    testonly = True,
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["bazel_utils.py"],
    ),
    imports = ["../.."],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-werks",
        "//tests/testlib/common:repo",
        requirement("pytest"),
        requirement("isort"),
        requirement("requirements-parser"),
        requirement("gitpython"),
    ],
)
