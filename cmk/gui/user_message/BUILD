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
        "//cmk/gui/dashboard",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/token_auth",
        "//cmk/gui/utils:csrf_token",
        "//cmk/gui/utils:flashed_messages",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
    ],
)
