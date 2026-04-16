load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "snapin_registry",
    srcs = [
        "_snapin/_base.py",
        "_snapin/_permission_section.py",
        "_snapin/_registry.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:i18n",
        "//cmk/gui:logged_in",
        "//cmk/gui:pages",
        "//cmk/gui:permissions",
        "//cmk/gui:type_defs",
        "//cmk/gui/pagetypes",
        "//cmk/gui/utils:roles",
        "//cmk/gui/valuespec",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:store",
    ],
)

filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "_snapin/_base.py",
            "_snapin/_permission_section.py",
            "_snapin/_registry.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
