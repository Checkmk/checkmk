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
    name = "htmllib",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/htmllib",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
        "//cmk/gui:auth_core",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:urls",
        "//cmk/gui/utils:user_errors",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:compare_html",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest-mock"),
        requirement("werkzeug"),
    ],
)
