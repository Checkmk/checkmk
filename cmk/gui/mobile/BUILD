load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "mobile",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:painter_options",
        "//cmk/gui/data_source",
        "//cmk/gui/pagetypes",
        "//cmk/gui/painter:v0_base",
        "//cmk/gui/userdb",
        "//cmk/gui/utils",
        "//cmk/gui/utils:middle",
        "//cmk/gui/views",
        "//cmk/gui/views:components",
        "//cmk/gui/visuals",
        "//packages/cmk-ccc:user",
    ],
)
