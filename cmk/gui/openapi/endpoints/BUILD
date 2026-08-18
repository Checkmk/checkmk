load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:doctest.bzl", "py_doc_test")

# Narrow target with the shared helpers used by both the legacy ``endpoints``
# package and the new-framework ``api_endpoints`` package. Extracting this
# lets ``api_endpoints`` depend on just these helpers without pulling in the
# full legacy ``endpoints`` library, breaking what would otherwise be a
# ``api_endpoints → endpoints → api_endpoints`` cycle.
py_library(
    name = "utils",
    srcs = ["utils.py"],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui:customer",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:groups_io",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client",
    ],
)

py_library(
    name = "endpoints",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["utils.py"],
    ),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":utils",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:session_context",
        "//cmk/gui/agent_registration",
        "//cmk/gui/fields",
        "//cmk/gui/fields:base",
        "//cmk/gui/form_specs",
        "//cmk/gui/graphing",
        "//cmk/gui/livestatus_utils/commands",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi/api_endpoints",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/openapi/shared_endpoint_families",
        "//cmk/gui/rest_api_types:notifications",
        "//cmk/gui/utils:middle",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:groups_io",
        "//cmk/gui/watolib:timeperiods",
        "//cmk/product_usage",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-web/cmk/web/utils",
        requirement("cryptography"),
        requirement("marshmallow"),
        requirement("marshmallow-oneofschema"),
        requirement("python-dateutil"),
        requirement("urllib3"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        ":endpoints",
        ":utils",
    ],
)
