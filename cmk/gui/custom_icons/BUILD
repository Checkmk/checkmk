load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "custom_icons",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:permissions",
        "//cmk/gui:table",
        "//cmk/gui:type_defs",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:csrf_token",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
        "//cmk/gui/valuespec",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:registries",
        "//cmk/utils",
    ],
)
