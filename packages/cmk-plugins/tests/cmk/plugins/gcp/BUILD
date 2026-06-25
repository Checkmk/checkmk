load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "gcp-test",
    size = "small",
    srcs = glob(["**/*.py"]),
    deps = [
        "//packages/cmk-plugins/cmk/plugins/gcp",
        requirement("google-cloud-asset"),
        requirement("google-cloud-monitoring"),
        requirement("polyfactory"),
        requirement("time-machine"),
    ],
)
