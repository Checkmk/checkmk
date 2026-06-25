load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "visuals",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/visuals",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui/bi",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/visuals",
        "//cmk/gui/wato",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest-mock"),
        requirement("time-machine"),
    ],
)
