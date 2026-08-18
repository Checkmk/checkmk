load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [":__subpackages__"],
    deps = [
        "//cmk/plugins",
        "//tests/testlib/unit",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

py_cmk_test(
    name = "update_config",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["**/conftest.py"],
    ),
    args = [
        "--random-order-bucket=global",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        ":conftest",
        "//cmk/update_config",
        "//packages/cmk-backup:utils",
        "//packages/cmk-ccc:store",
        "//packages/cmk-werks:site",
        "//packages/cmk-wsgi",
        "//tests/unit:conftest",
        requirement("flask"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("pytest-mock"),
    ],
)
