load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "logwatch",
    srcs = [
        "__init__.py",
        "_page.py",
        "_rulespecs.py",
        "register.py",
    ],
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
        "//cmk/gui:view_toolkit",
        "//cmk/gui/search",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
        "//cmk/gui/valuespec",
        "//cmk/gui/views",
        "//cmk/gui/wato",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:registries",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
    ],
)
