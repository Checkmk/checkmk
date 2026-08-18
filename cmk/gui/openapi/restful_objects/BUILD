load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:doctest.bzl", "py_doc_test")

py_library(
    name = "type_defs",
    srcs = ["type_defs.py"],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages/cmk-wsgi:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        requirement("marshmallow"),
    ],
)

py_library(
    name = "restful_objects",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "type_defs.py",
        ],
    ),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages/cmk-wsgi:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":type_defs",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/fields",
        "//cmk/gui/fields:base",
        "//cmk/gui/livestatus_utils/commands",
        "//cmk/gui/openapi:permission_tracking",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi/framework:api_config",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:timeperiods",
        "//cmk/utils",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:tar-archive",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-web/cmk/web/utils",
        requirement("jinja2"),
        requirement("marshmallow"),
        requirement("marshmallow-oneofschema"),
        requirement("werkzeug"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":restful_objects"],
)
