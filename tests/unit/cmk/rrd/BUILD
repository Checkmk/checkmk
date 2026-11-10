load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "rrd",
    size = "small",
    srcs = glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/rrd",
        "//packages/cmk-ccc:config-path",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:store",
        "@rrdtool//:rrdtool_python_lib",
        requirement("pytest-random-order"),
    ],
)
