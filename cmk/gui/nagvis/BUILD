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
        "//cmk/gui:config",
        "//cmk/gui:groups",
        "//cmk/gui:hooks",
        "//cmk/gui:i18n",
        "//cmk/gui:logged_in",
        "//cmk/gui:pages",
        "//cmk/gui:permissions",
        "//cmk/gui:type_defs",
        "//cmk/gui/htmllib:foldable_container",
        "//cmk/gui/htmllib:html",
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
