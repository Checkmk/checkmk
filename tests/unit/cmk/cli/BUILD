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
        "//cmk/cli/engine",
        "//cmk/cli/engine:run",
        "//packages/cmk-plugin-apis:cli",
        requirement("pytest-random-order"),
    ],
)
