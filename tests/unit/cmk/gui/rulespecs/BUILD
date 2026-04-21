load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "rulespecs",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/rulespecs"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:exceptions",
        "//cmk/gui:i18n",
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
