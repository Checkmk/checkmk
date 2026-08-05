load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "agent_download",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/fields",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/openapi/shared_endpoint_families",
        "//cmk/gui/token_auth",
        "//cmk/gui/utils:middle",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:registries",
        "//cmk/utils",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:version",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-web/cmk/web/utils",
    ],
)
