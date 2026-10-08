load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "aws_v2-test",
    size = "small",
    srcs = glob(
        ["**/*.py"],
        exclude = ["component/**"],
    ),
    deps = [
        "//packages/cmk-plugins/cmk/plugins/aws_v2",
        requirement("mypy-boto3-logs"),
        requirement("python-dateutil"),
    ],
)

py_cmk_test(
    name = "aws_v2-component-test",
    size = "medium",
    srcs = glob(["component/**/*.py"]),
    deps = [
        "//packages/cmk-plugins/cmk/plugins/aws_v2",
        "//packages/cmk-plugins/cmk/testlib/aws_v2",
    ],
)
