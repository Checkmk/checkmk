load("@aspect_rules_py//py:defs.bzl", "py_library")
load("//bazel/rules:doctest.bzl", "py_doc_test")

py_library(
    name = "inventory",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:visual_link",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:api_config",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/framework:types",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:permission_verification",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:speaklater",
        "//cmk/gui/valuespec",
        "//cmk/gui/views:components",
        "//cmk/gui/visuals",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:groups_io",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//packages/cmk-inventory:inventory",
        "//packages/cmk-plugin-apis:inventory_ui",
        "//packages/cmk-ruleset-matcher",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":inventory"],
)
