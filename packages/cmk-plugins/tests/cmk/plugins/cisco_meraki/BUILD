load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "cisco_meraki-test",
    size = "small",
    srcs = glob(["**/*.py"]),
    deps = [
        "//packages/cmk-plugins/cmk/plugins/cisco_meraki",
        requirement("meraki"),
        requirement("polyfactory"),
        requirement("time-machine"),
    ],
)
