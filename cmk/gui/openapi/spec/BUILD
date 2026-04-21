load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "utils",
    srcs = ["utils.py"],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/openapi/framework:api_config",
        "//cmk/gui/openapi/restful_objects:type_defs",
    ],
)

py_library(
    name = "spec",
    srcs = [
        "__init__.py",
        "plugin_marshmallow.py",
        "plugin_pydantic.py",
    ],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":utils",
        "//cmk/gui/fields:base",
        "//cmk/gui/openapi:_type_adapter",
        "//cmk/gui/openapi/framework:types",
        requirement("apispec"),
        requirement("marshmallow"),
        requirement("marshmallow-oneofschema"),
        requirement("pydantic"),
    ],
)
