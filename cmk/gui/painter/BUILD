load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "painter",
    srcs = [
        "__init__.py",
        "base.py",
        "helpers.py",
        "host_tag_painters.py",
        "registry.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:painter_options",
        "//cmk/gui/utils:middle",
        "//cmk/gui/valuespec",
        "//cmk/gui/visuals",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-web/cmk/web/utils",
    ],
)

py_library(
    name = "painters",
    srcs = ["painters.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":painter",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:painter_options",
        "//cmk/gui:visual_link",
        "//cmk/gui/graphing",
        "//cmk/gui/utils:base",
        "//cmk/gui/utils:middle",
        "//cmk/gui/valuespec",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-web/cmk/web/utils",
    ],
)
