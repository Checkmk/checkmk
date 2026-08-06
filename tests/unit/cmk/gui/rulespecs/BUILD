load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "rulespecs",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/rulespecs",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui/form_specs",
        "//cmk/gui/graphing",
        "//cmk/gui/inventory",
        "//cmk/gui/rule_specs:legacy_converter",
        "//cmk/gui/rule_specs:types",
        "//cmk/gui/utils",
        "//cmk/gui/utils:middle",
        "//cmk/gui/valuespec",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:password_store",
        "//cmk/gui/watolib:timeperiods",
        "//packages/cmk-ccc:version",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-ruleset-matcher",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
    ],
)
