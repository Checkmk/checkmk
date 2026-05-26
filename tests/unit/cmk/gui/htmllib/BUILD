load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_test(
    name = "htmllib",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--import-mode=importlib",
        "tests/unit/cmk/gui/htmllib",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
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
