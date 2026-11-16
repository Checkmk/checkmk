load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "crypto",
    size = "small",
    srcs = glob(["**/*.py"]),
    deps = [
        "//packages/cmk-ccc:regex",
        "//packages/cmk-crypto",
    ],
)
