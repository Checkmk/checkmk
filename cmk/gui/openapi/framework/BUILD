load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:doctest.bzl", "py_doc_test")

py_library(
    name = "api_config",
    srcs = ["api_config.py"],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//packages/cmk-wsgi:__pkg__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "types",
    srcs = [
        "_types.py",
        "_utils.py",
        "content_types.py",
        "exceptions.py",
        "model/__init__.py",
        "model/_api_field.py",
        "model/_api_model.py",
        "model/dynamic_fields.py",
        "model/headers.py",
        "model/omitted.py",
        "utils.py",
    ],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages/cmk-wsgi:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/openapi:_type_adapter",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/utils:middle",
        requirement("pydantic"),
        requirement("werkzeug"),
    ],
)

py_library(
    name = "core",
    srcs = [
        "_context.py",
        "model/response.py",
        "registry.py",
        "versioned_endpoint.py",
    ],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages/cmk-wsgi:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":types",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/token_auth",
        "//cmk/gui/utils:middle",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-ruleset-matcher",
        "//packages/cmk-web/cmk/web/utils",
        requirement("werkzeug"),
    ],
)

py_library(
    name = "framework",
    srcs = [
        "__init__.py",
        "_validation.py",
        "disabled_endpoint.py",
        "endpoint_link.py",
        "endpoint_model.py",
        "handler.py",
        "model/base_models.py",
        "model/common_fields.py",
        "model/constructors.py",
        "model/converter.py",
        "model/restrict_editions.py",
        "model/restrict_features.py",
    ],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages/cmk-wsgi:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":core",
        ":types",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:customer",
        "//cmk/gui/fields",
        "//cmk/gui/openapi:versioned_endpoint_map",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:middle",
        "//cmk/gui/valuespec",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:groups_io",
        "//cmk/gui/watolib:passwords",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-licensing",
        requirement("werkzeug"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        ":framework",
        ":types",
    ],
)
