load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "cli",
    size = "small",
    srcs = glob(["**/*.py"]),
    args = ["--random-order-bucket=global"],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/base:base-app",
        "//cmk/plugins/checkmk/cli",
        "//tests/testlib/unit",
        "//tests/unit:conftest",
        requirement("pytest-random-order"),
    ],
)
