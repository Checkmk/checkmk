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
        "generate_api_spec.py",
    ],
    imports = ["../../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/openapi:openapi_init",
        "//cmk/gui/openapi:versioned_endpoint_map",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:api_config",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/framework:types",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/openapi/spec",
        "//cmk/gui/openapi/spec/editions",
        "//cmk/gui/utils:permission_verification",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        requirement("apispec"),
        requirement("apispec-oneofschema"),
        requirement("jinja2"),
        requirement("marshmallow"),
        requirement("pydantic"),
        requirement("pyyaml"),
        requirement("werkzeug"),
    ],
)
