load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "page_token_error",
    srcs = ["page_token_error.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
    ],
)

py_library(
    name = "type_defs",
    srcs = ["type_defs.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui/valuespec",
    ],
)

py_library(
    name = "dashboard",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "page_token_error.py",
            "type_defs.py",
        ],
    ),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":page_token_error",
        ":type_defs",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:main_navigation",
        "//cmk/gui:ntop",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:painter_options",
        "//cmk/gui:session_context",
        "//cmk/gui/data_source",
        "//cmk/gui/fields",
        "//cmk/gui/graphing",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/framework:types",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/pagetypes",
        "//cmk/gui/painter:v0_base",
        "//cmk/gui/plugins/dashboard",
        "//cmk/gui/sidebar/_snapin:snapin_registry",
        "//cmk/gui/token_auth",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:urls",
        "//cmk/gui/valuespec",
        "//cmk/gui/views",
        "//cmk/gui/views:store",
        "//cmk/gui/visuals",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:groups_io",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client",
        requirement("annotated-types"),
        requirement("pydantic"),
        requirement("python-dateutil"),
    ],
)
