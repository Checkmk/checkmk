load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "utils",
    srcs = ["utils.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/utils",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:store",
        "//packages/cmk-livestatus-client:py_livestatus",
    ],
)

py_library(
    name = "topology",
    srcs = [
        "filters.py",
        "frontend_texts.py",
        "topology.py",
        "type_defs.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":utils",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/data_source",
        "//cmk/gui/pagetypes",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:speaklater",
        "//cmk/gui/utils:urls",
        "//cmk/gui/views",
        "//cmk/gui/views:icon",
        "//cmk/gui/views:page_ajax_filters",
        "//cmk/gui/views:store",
        "//cmk/gui/visuals",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
    ],
)

py_library(
    name = "nodevis",
    srcs = [
        "__init__.py",
        "aggregation.py",
        "nodevis.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":topology",
        ":utils",
        "//cmk/bi",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/bi",
        "//cmk/gui/utils:csrf_token",
        "//cmk/gui/views",
        "//cmk/gui/views:icon",
        "//cmk/gui/views:store",
        "//cmk/gui/visuals",
        "//packages/cmk-ccc:user",
    ],
)
