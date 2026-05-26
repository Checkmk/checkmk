load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "community",
    srcs = ["__init__.py"],
    imports = ["../../../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/agent_registration",
        "//cmk/gui/availability",
        "//cmk/gui/background_job/wato",
        "//cmk/gui/bi",
        "//cmk/gui/dashboard",
        "//cmk/gui/data_source",
        "//cmk/gui/inventory",
        "//cmk/gui/ldap_integration",
        "//cmk/gui/mkeventd",
        "//cmk/gui/monitor/hosts",
        "//cmk/gui/openapi:openapi_init",
        "//cmk/gui/openapi:registration",
        "//cmk/gui/openapi/endpoints",
        "//cmk/gui/pagetypes",
        "//cmk/gui/sidebar",
        "//cmk/gui/user_message",
        "//cmk/gui/views:_openapi",
        "//cmk/gui/views:command",
        "//cmk/gui/visuals",
        "//cmk/gui/wato:base",
    ],
)

py_binary(
    name = "generate_api_spec",
    srcs = ["//cmk/gui/openapi/spec/spec_generator:generate_api_spec.py"],
    imports = ["../../../../../.."],
    main = "generate_api_spec.py",
    visibility = ["//:__subpackages__"],
    deps = [
        ":community",
        "//cmk/gui:config",
        "//cmk/gui/openapi/spec/editions",
        "//cmk/gui/openapi/spec/spec_generator",
        "//cmk/gui/plugins/wato/check_parameters:stub",
        requirement("apispec"),
        requirement("apispec-oneofschema"),
        requirement("pyyaml"),
    ],
)
