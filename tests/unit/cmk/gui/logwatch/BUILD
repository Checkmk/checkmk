load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "logwatch",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/logwatch"],
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui/logwatch",
        "//packages/cmk-ccc:hostaddress",
    ],
)
