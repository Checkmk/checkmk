load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "crash_reporting",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/crash_reporting"],
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui/crash_reporting",
        "//packages/cmk-crash:crash",
        "//packages/cmk-livestatus-client:py_livestatus",
        requirement("polyfactory"),
        requirement("werkzeug"),
    ],
)
