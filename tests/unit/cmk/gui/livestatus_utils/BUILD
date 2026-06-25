load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "livestatus_utils",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/livestatus_utils",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:app",
        "//cmk/gui:config",
        "//cmk/gui:session_context",
        "//cmk/gui/livestatus_utils/commands",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("python-dateutil"),
    ],
)
