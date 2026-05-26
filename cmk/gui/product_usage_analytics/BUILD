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
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:urls",
        "//cmk/gui/valuespec",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/product_usage",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)
