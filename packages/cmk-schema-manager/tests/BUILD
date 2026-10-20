load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["**/*.py"]),
    deps = [
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-schema-manager",
        "//packages/cmk-schema-manager:testlib",
    ],
)
