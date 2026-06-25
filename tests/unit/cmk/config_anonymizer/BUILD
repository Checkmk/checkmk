load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [":__subpackages__"],
    deps = [
        "//cmk/base:config",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//tests/testlib/unit",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

py_cmk_test(
    name = "config_anonymizer",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["**/conftest.py"],
    ),
    args = [
        "--random-order-bucket=global",
        "--dist=loadfile",
        "--numprocesses=4",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        ":conftest",
        "//cmk/config_anonymizer",
        "//cmk/update_config",
        "//tests/testlib/unit",
        "//tests/unit:conftest",
        requirement("flask"),
        requirement("pytest-mock"),
        requirement("pytest-random-order"),
        requirement("pytest-xdist"),
    ],
)
