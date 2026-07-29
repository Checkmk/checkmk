load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["**/*.py"]),
    data = glob(["**/tree_test_data/**"]),
    deps = [
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:store",
        "//packages/cmk-inventory:inventory",
    ],
)
