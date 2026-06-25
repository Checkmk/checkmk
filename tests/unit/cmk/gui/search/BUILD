load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "search",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/search",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:session_context",
        "//cmk/gui/background_job/process",
        "//cmk/gui/search",
        "//cmk/gui/utils:roles",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("fakeredis"),
        requirement("polyfactory"),
        requirement("pytest-mock"),
        requirement("redis"),
        requirement("werkzeug"),
    ],
)
