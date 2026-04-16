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
        "//cmk/gui:i18n",
        "//cmk/gui:page_menu",
        "//cmk/gui:sites",
        "//cmk/gui:type_defs",
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
        "//cmk/gui:breadcrumb",
        "//cmk/gui:config",
        "//cmk/gui:cron",
        "//cmk/gui:ctx_stack",
        "//cmk/gui:exceptions",
        "//cmk/gui:header",
        "//cmk/gui:hooks",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:log",
        "//cmk/gui:logged_in",
        "//cmk/gui:main_menu",
        "//cmk/gui:page_menu",
        "//cmk/gui:pages",
        "//cmk/gui:permissions",
        "//cmk/gui:sites",
        "//cmk/gui:theme",
        "//cmk/gui:type_defs",
        "//cmk/gui:view",
        "//cmk/gui/data_source",
        "//cmk/gui/htmllib:html",
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

# Temporary: nodevis files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once nodevis is fully extracted.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "filters.py",
            "frontend_texts.py",
            "topology.py",
            "type_defs.py",
            "utils.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
