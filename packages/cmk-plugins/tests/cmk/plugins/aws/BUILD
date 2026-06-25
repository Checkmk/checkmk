load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "aws-test",
    size = "small",
    srcs = glob(["**/*.py"]),
    deps = [
        "//packages/cmk-plugins/cmk/plugins/aws",
        requirement("mypy-boto3-logs"),
        requirement("polyfactory"),
        requirement("python-dateutil"),
        requirement("requests"),
    ],
)
