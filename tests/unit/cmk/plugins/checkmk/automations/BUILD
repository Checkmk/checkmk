load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "automations",
    size = "small",
    srcs = glob(["**/*.py"]),
    args = ["--random-order-bucket=global"],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/base",
        "//cmk/plugins",
        "//cmk/plugins/checkmk/automations",
        "//tests/testlib/unit",
        "//tests/unit:conftest",
        requirement("pytest-random-order"),
    ],
)
