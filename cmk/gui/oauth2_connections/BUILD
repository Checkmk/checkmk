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
        "//cmk/gui:exceptions",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:passwords",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
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
        "//cmk/gui:breadcrumb",
        "//cmk/gui:config",
        "//cmk/gui:default_permissions",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:logged_in",
        "//cmk/gui:page_menu",
        "//cmk/gui:pages",
        "//cmk/gui:permissions",
        "//cmk/gui:site_config",
        "//cmk/gui:table",
        "//cmk/gui:type_defs",
        "//cmk/gui:user_sites",
        "//cmk/gui/form_specs",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:passwords",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        requirement("requests"),
    ],
)
