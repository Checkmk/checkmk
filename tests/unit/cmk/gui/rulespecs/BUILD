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
    name = "rulespecs",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/rulespecs",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/form_specs",
        "//cmk/gui/graphing",
        "//cmk/gui/inventory",
        "//cmk/gui/rule_specs:legacy_converter",
        "//cmk/gui/rule_specs:types",
        "//cmk/gui/utils:autocompleter_config",
        "//cmk/gui/utils:urls",
        "//cmk/gui/valuespec",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:password_store",
        "//cmk/gui/watolib:timeperiods",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-plugin-apis:rulesets",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
    ],
)
