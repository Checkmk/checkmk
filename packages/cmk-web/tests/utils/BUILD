load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:user",
        "//packages/cmk-web:context",
        "//packages/cmk-web/cmk/web/utils",
    ],
)
