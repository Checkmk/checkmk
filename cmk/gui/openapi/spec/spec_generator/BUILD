load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files(["generate_api_spec.py"])

py_library(
    name = "spec_generator",
    srcs = [
        "__init__.py",
        "_code_examples.py",
        "_doc_marshmallow.py",
        "_doc_pydantic.py",
        "_doc_utils.py",
        "_type_defs.py",
    ],
    imports = ["../../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:http",
        "//cmk/gui:permissions",
        "//cmk/gui/openapi:openapi_init",
        "//cmk/gui/openapi:versioned_endpoint_map",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/framework:types",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/openapi/spec",
        "//cmk/gui/openapi/spec:utils",
        "//cmk/gui/utils:permission_verification",
        requirement("apispec"),
        requirement("jinja2"),
        requirement("marshmallow"),
        requirement("pydantic"),
        requirement("werkzeug"),
    ],
)

py_library(
    name = "_core",
    srcs = ["_core.py"],
    imports = ["../../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":spec_generator",
        "//cmk/gui:main_modules",
        "//cmk/gui:script_helpers",
        "//cmk/gui:session",
        "//cmk/gui:session_context",
        "//cmk/gui/openapi:versioned_endpoint_map",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:api_config",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/framework:types",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/openapi/spec",
        "//cmk/gui/openapi/spec:utils",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        requirement("apispec"),
        requirement("apispec-oneofschema"),
        requirement("openapi-spec-validator"),
    ],
)
