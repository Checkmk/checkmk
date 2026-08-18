load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "watolib_store",
    srcs = ["watolib/store.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:passwords",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
    ],
)

py_library(
    name = "oauth2_connections",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["watolib/store.py"],
    ),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":watolib_store",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/form_specs",
        "//cmk/gui/utils:middle",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:passwords",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-web/cmk/web/utils",
        requirement("requests"),
    ],
)
