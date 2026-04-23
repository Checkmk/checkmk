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
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["conftest.py"],
    ),
    data = [
        "//cmk/plugins:checkman_community",
        "//cmk/plugins:libexec",
        "//packages/cmk-plugins:checkman_all",
        "//packages/cmk-plugins:libexec_all",
    ],
    pytest_main = True,
    deps = [
        ":conftest",
        "//:pyproject-toml",
        "//cmk/checkengine",
        "//cmk/plugins:plugins_community",
        "//tests/plugins_consistency/common_tests",
        "//tests/testlib/unit",
        requirement("pytest-mock"),
        requirement("pytest"),
    ],
)
