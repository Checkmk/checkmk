load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:doctest.bzl", "py_doc_test")

py_library(
    name = "ldap_integration",
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
        "//cmk/gui:customer",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/fields",
        "//cmk/gui/fields:base",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi/endpoints",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/openapi/shared_endpoint_families",
        "//cmk/gui/userdb",
        "//cmk/gui/utils",
        "//cmk/gui/utils:middle",
        "//cmk/gui/valuespec",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:groups_io",
        "//cmk/utils",
        "//packages/cmk-web/cmk/web/utils",
        requirement("marshmallow"),
        requirement("marshmallow-oneofschema"),
        requirement("python-active-directory"),
        requirement("python-ldap"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":ldap_integration"],
)
