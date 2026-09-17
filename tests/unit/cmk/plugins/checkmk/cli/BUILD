load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "cli",
    size = "small",
    srcs = glob(["**/*.py"]),
    args = ["--random-order-bucket=global"],
    env = {"EDITION": "community"},
    tags = [
        # cmk.base.community_app comes from here; the linter maps it elsewhere.
        "deballast-keep=//cmk/base:app",
    ],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/base:app",
        "//cmk/plugins/checkmk/cli",
        "//tests/testlib/common:empty_config",
        "//tests/testlib/unit",
        "//tests/unit:conftest",
        requirement("pytest-random-order"),
    ],
)
