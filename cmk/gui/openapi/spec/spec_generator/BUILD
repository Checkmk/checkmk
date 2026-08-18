load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:doctest.bzl", "py_doc_test")

exports_files(["generate_api_spec.py"])

py_binary(
    name = "merge_api_specs",
    srcs = ["merge_api_specs.py"],
    main = "merge_api_specs.py",
    visibility = ["//:__subpackages__"],
    deps = [
        "//packages/cmk-ccc:version",
        requirement("pyyaml"),
    ],
)

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
        "merge_api_specs.py",
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
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-web/cmk/web/utils",
        requirement("apispec"),
        requirement("apispec-oneofschema"),
        requirement("jinja2"),
        requirement("marshmallow"),
        requirement("pydantic"),
        requirement("pyyaml"),
        requirement("werkzeug"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":spec_generator"],
)
