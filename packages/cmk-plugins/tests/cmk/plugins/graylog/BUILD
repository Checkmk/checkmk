load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "graylog-test",
    size = "small",
    srcs = glob(["**/*.py"]),
    data = glob(["**/*.yaml"]),
    deps = [
        "//packages/cmk-plugins/cmk/plugins/graylog",
        requirement("time-machine"),
        requirement("vcrpy"),
    ],
)
