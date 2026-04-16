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
        "//cmk/gui:hooks",
        "//cmk/gui:i18n",
        "//cmk/gui:sites",
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
        "//cmk/gui:hooks",
        "//cmk/gui:i18n",
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
        "//cmk/gui:config",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:logged_in",
        "//cmk/gui:theme",
        "//cmk/gui:type_defs",
        "//cmk/gui:view_utils",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:urls",
    ],
)

filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "_compiler.py",
            "bi_manager.py",
            "foldable_tree_renderer.py",
            "helpers.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
