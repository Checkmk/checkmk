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
    name = "sidebar",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/sidebar",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/search",
        "//cmk/gui/sidebar",
        "//cmk/gui/utils:labels",
        "//cmk/gui/utils:roles",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest-mock"),
        requirement("werkzeug"),
    ],
)
