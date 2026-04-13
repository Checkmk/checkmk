load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "type_defs",
    srcs = ["type_defs.py"],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:http",
        requirement("marshmallow"),
    ],
)

py_library(
    name = "restful_objects",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "request_schemas.py",
            "type_defs.py",
            "versioned_endpoint_map.py",
        ],
    ),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":type_defs",
        "//cmk/gui:config",
        "//cmk/gui:exceptions",
        "//cmk/gui:hooks",
        "//cmk/gui:http",
        "//cmk/gui/fields",
        "//cmk/gui/fields:base",
        "//cmk/gui/openapi:permission_tracking",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/utils:permission_verification",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:timeperiods",
        "//cmk/utils",
        "//packages/cmk-ccc:archive",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client:py_livestatus",
        requirement("jinja2"),
        requirement("marshmallow"),
        requirement("marshmallow-oneofschema"),
        requirement("werkzeug"),
    ],
)

# Temporary: restful_objects files that still belong to the monolithic //cmk/gui target.
filegroup(
    name = "gui_srcs",
    srcs = [
        "request_schemas.py",
        "versioned_endpoint_map.py",
    ],
    visibility = ["//cmk/gui:__pkg__"],
)
