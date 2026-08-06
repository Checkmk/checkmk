load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "utils",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/utils",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:app",
        "//cmk/gui:auth",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:ntop",
        "//cmk/gui/userdb",
        "//cmk/gui/utils",
        "//cmk/gui/utils:base",
        "//cmk/gui/utils:middle",
        "//cmk/gui/visuals",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        "//packages/cmk-licensing",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//packages/cmk-wsgi",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("flask"),
        requirement("pytest-mock"),
        requirement("werkzeug"),
    ],
)
