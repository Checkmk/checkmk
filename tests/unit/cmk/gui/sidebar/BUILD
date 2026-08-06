load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "sidebar",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/sidebar",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/search:matchers",
        "//cmk/gui/search:quicksearch",
        "//cmk/gui/sidebar",
        "//cmk/gui/utils",
        "//cmk/gui/utils:middle",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest-mock"),
        requirement("werkzeug"),
    ],
)
