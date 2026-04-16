load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "snapin_registry",
    srcs = [
        "_base.py",
        "_permission_section.py",
        "_registry.py",
    ],
    imports = ["../../../.."],
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
        requirement("pydantic"),
    ],
)

filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "_base.py",
            "_permission_section.py",
            "_registry.py",
        ],
    ),
    visibility = ["//cmk/gui/sidebar:__pkg__"],
)
