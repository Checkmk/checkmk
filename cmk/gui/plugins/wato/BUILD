load("@aspect_rules_py//py:defs.bzl", "py_library")
load("//bazel/rules:doctest.bzl", "py_doc_test")

py_library(
    name = "wato",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
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
        "//cmk/gui/form_specs",
        "//cmk/gui/inventory",
        "//cmk/gui/utils:middle",
        "//cmk/gui/valuespec",
        "//cmk/gui/wato",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:password_store",
        "//packages/cmk-ccc:site",
        "//packages/cmk-plugins:aws",
        "//packages/cmk-web/cmk/web/utils",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":wato"],
)
