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
    name = "views",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--import-mode=importlib",
        "tests/unit/cmk/gui/views",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:general_pages",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:painter_options",
        "//cmk/gui/data_source",
        "//cmk/gui/inventory",
        "//cmk/gui/painter:v0_base",
        "//cmk/gui/plugins/views",
        "//cmk/gui/utils:html",
        "//cmk/gui/views",
        "//cmk/gui/visuals",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("flask"),
        requirement("pytest-mock"),
    ],
)
