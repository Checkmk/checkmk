load("@aspect_rules_py//py:defs.bzl", "py_library", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [":__subpackages__"],
    deps = [
        "//cmk/base:config",  # hidden in a local import
        "//cmk/checkengine",
        requirement("pytest"),
    ],
)

py_test(
    name = "community",
    srcs = glob(["**/*.py"]),
    pytest_main = True,
    deps = [
        ":conftest",
        "//:pyproject-toml",
        "//cmk/editions:community",
        "//tests/plugins_consistency/common_tests",
        "//tests/testlib/unit",
        requirement("pytest-mock"),
        requirement("pytest"),
    ],
)
