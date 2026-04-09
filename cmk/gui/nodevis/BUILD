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

# Temporary: nodevis files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once nodevis is fully extracted.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["utils.py"],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
