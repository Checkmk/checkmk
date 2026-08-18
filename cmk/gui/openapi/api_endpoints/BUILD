load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:doctest.bzl", "py_doc_test")

py_library(
    name = "api_endpoints",
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
        "//cmk/gui/background_job/job",
        "//cmk/gui/fields",
        "//cmk/gui/fields:base",
        "//cmk/gui/livestatus_utils/commands",
        "//cmk/gui/oauth2_connections:watolib_store",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi/endpoints:utils",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/framework:types",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/openapi/shared_endpoint_families",
        "//cmk/gui/openapi/spec:utils",
        "//cmk/gui/quick_setup",
        "//cmk/gui/rest_api_types:notifications",
        "//cmk/gui/token_auth",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:middle",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:groups_io",
        "//cmk/gui/watolib:passwords",
        "//cmk/utils",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        "//packages/cmk-events",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-web/cmk/web/utils",
        requirement("python-dateutil"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":api_endpoints"],
)
