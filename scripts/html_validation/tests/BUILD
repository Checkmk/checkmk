load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "tests",
    size = "small",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    deps = [
        "//scripts/html_validation",
    ],
)
