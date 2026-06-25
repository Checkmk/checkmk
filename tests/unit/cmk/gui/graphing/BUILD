load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "graphing",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/graphing",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui/graphing",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:temperate_unit",
        "//cmk/utils",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("time-machine"),
    ],
)
