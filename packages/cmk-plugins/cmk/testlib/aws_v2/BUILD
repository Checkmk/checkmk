load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "aws_v2",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = ["//packages/cmk-plugins/tests/cmk/plugins/aws_v2:__pkg__"],
)
