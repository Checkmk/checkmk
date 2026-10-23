load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "ibm_svc-test",
    size = "small",
    srcs = glob(["**/*.py"]),
    deps = [
        "//packages/cmk-plugins/cmk/plugins/ibm_svc",
    ],
)
