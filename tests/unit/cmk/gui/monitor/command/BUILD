load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "command",
    srcs = glob(["**/*.py"]),
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui/monitor/command",
    ],
)
