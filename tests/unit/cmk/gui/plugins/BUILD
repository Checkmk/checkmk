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
    name = "plugins",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/plugins",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:painter_options",
        "//cmk/gui:visual_link",
        "//cmk/gui/data_source",
        "//cmk/gui/form_specs",
        "//cmk/gui/graphing",
        "//cmk/gui/inventory",
        "//cmk/gui/painter:v0_base",
        "//cmk/gui/plugins/wato",
        "//cmk/gui/plugins/wato/check_parameters",
        "//cmk/gui/rule_specs:legacy_converter",
        "//cmk/gui/sidebar",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:roles",
        "//cmk/gui/valuespec",
        "//cmk/gui/views",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//packages/cmk-plugins:azure_deprecated",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)
