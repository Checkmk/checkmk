load("@aspect_rules_py//py:defs.bzl", "py_library")

# Leaf target exposing wato types/helpers that feature modules need (quick_setup,
# mkeventd, ldap_integration, oauth2_connections, backup, ...). This lets features
# depend on wato:base without creating a cycle with the rest of wato, which in turn
# depends on those features for registration.
py_library(
    name = "base",
    srcs = [
        "_group_selection.py",
        "_main_module_topics.py",
        "_permissions.py",
        "pages/_password_store_valuespecs.py",
        "pages/_simple_modes.py",
        "pages/_tile_menu.py",
        "pages/global_settings.py",
        "pages/userdb_common.py",
        "piggyback_hub.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:breadcrumb",
        "//cmk/gui:config",
        "//cmk/gui:customer",
        "//cmk/gui:default_name",
        "//cmk/gui:exceptions",
        "//cmk/gui:global_config",
        "//cmk/gui:groups",
        "//cmk/gui:hooks",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:log",
        "//cmk/gui:logged_in",
        "//cmk/gui:page_menu",
        "//cmk/gui:site_config",
        "//cmk/gui:table",
        "//cmk/gui:type_defs",
        "//cmk/gui:user_connection_config_types",
        "//cmk/gui/form_specs",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/search",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:csrf_token",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:flashed_messages",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
        "//cmk/gui/valuespec",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:groups_io",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
    ],
)

# Temporary: wato files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once wato is fully extracted.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "_group_selection.py",
            "_main_module_topics.py",
            "_permissions.py",
            "pages/_password_store_valuespecs.py",
            "pages/_simple_modes.py",
            "pages/_tile_menu.py",
            "pages/global_settings.py",
            "pages/userdb_common.py",
            "piggyback_hub.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
