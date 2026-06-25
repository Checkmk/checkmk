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
    name = "dashboard",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/dashboard",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/dashboard",
        "//cmk/gui/graphing",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/token_auth",
        "//cmk/gui/utils:temperate_unit",
        "//cmk/gui/views:icon",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest-mock"),
    ],
)
