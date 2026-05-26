load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "nagvis",
    srcs = glob(["**/*.py"]),
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
        "//cmk/gui:page_toolkit",
        "//cmk/gui/sidebar",
        "//cmk/gui/sidebar/_snapin:snapin_registry",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:roles",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:groups_io",
        "//cmk/utils",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
    ],
)
