load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "user_message",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:messaging",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/utils",
        "//cmk/gui/utils:middle",
        "//packages/cmk-web/cmk/web/utils",
    ],
)
