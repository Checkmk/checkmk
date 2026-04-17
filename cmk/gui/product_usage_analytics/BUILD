load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "product_usage_analytics",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:default_permissions",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:logged_in",
        "//cmk/gui:pages",
        "//cmk/gui:permissions",
        "//cmk/gui:type_defs",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/utils:html",
        "//cmk/gui/valuespec",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/product_usage",
        "//cmk/utils",
    ],
)
