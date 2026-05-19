load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "bi_manager",
    srcs = ["bi_manager.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/bi",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
    ],
)

py_library(
    name = "_compiler",
    srcs = ["_compiler.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":bi_manager",
        "//cmk/bi",
        "//cmk/gui:core_toolkit",
    ],
)

py_library(
    name = "helpers",
    srcs = ["helpers.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:hostaddress",
    ],
)

py_library(
    name = "foldable_tree_renderer",
    srcs = ["foldable_tree_renderer.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":helpers",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:urls",
    ],
)

py_library(
    name = "bi",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "_compiler.py",
            "bi_manager.py",
            "foldable_tree_renderer.py",
            "helpers.py",
        ],
    ),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":_compiler",
        ":bi_manager",
        ":foldable_tree_renderer",
        "//cmk/bi",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:customer",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:painter_options",
        "//cmk/gui/data_source",
        "//cmk/gui/fields",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/painter:v0_base",
        "//cmk/gui/sidebar",
        "//cmk/gui/utils:csrf_token",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:permission_verification",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:selection_id",
        "//cmk/gui/utils:speaklater",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
        "//cmk/gui/utils:user_errors",
        "//cmk/gui/valuespec",
        "//cmk/gui/views:command",
        "//cmk/gui/views:icon",
        "//cmk/gui/visuals",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:groups_io",
        "//cmk/gui/watolib:registries",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client",
    ],
)
