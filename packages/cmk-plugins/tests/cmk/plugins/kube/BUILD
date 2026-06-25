load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "kube-test",
    size = "small",
    srcs = glob(["**/*.py"]),
    deps = [
        "//packages/cmk-plugins/cmk/plugins/kube",
        requirement("kubernetes"),
        requirement("polyfactory"),
        requirement("pytest-mock"),
        requirement("requests"),
    ],
)
