load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [":__subpackages__"],
    deps = [
        "//cmk/base:config",  # hidden in a local import
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "community",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["conftest.py"],
    ),
    data = [
        "//cmk/plugins:checkman",
        "//cmk/plugins:libexec",
        "//packages/cmk-plugins:checkman_all",
        "//packages/cmk-plugins:libexec_all",
    ],
    deps = [
        ":conftest",
        "//:pyproject-toml",
        "//cmk/plugins",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//tests/plugins_consistency/common_tests",
        "//tests/testlib/unit",
        requirement("pytest-mock"),
    ],
)
