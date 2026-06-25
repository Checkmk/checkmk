load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "search",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/search",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
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
