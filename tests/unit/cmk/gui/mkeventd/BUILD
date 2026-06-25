load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "mkeventd",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/mkeventd",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui/mkeventd",
        "//cmk/gui/search",
        "//cmk/gui/utils:roles",
        "//cmk/gui/views:icon",
        "//packages/cmk-ec",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("time-machine"),
    ],
)
