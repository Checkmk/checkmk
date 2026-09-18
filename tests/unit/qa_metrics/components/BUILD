load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "tests",
    size = "small",
    srcs = [
        "__init__.py",
        "test_ownership.py",
    ],
    imports = ["../../../.."],
    deps = ["//tests/qa_metrics/components"],
)
