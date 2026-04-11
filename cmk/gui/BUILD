load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files([
    ".f12",
])

py_library(
    name = "exceptions",
    srcs = ["exceptions.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:exceptions",
        requirement("werkzeug"),
    ],
)

py_library(
    name = "ctx_stack",
    srcs = ["ctx_stack.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("flask"),
        requirement("werkzeug"),
    ],
)

py_library(
    name = "log",
    srcs = ["log.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-trace",
    ],
)

py_library(
    name = "hooks",
    srcs = ["hooks.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-trace",
    ],
)

py_library(
    name = "role_types",
    srcs = ["role_types.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "site_config",
    srcs = ["site_config.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
    ],
)

py_library(
    name = "features",
    srcs = ["features.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
    ],
)

py_library(
    name = "type_defs",
    srcs = ["type_defs.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":exceptions",
        "//cmk/gui/utils:speaklater",
        "//cmk/inventory",
        "//cmk/utils",
        "//packages/cmk-ccc:cpu-tracking",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-crypto",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        requirement("pydantic"),
    ],
)

py_library(
    name = "i18n",
    srcs = ["i18n.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":ctx_stack",
        ":hooks",
        "//cmk/gui/utils:speaklater",
        "//cmk/utils",
    ],
)

py_library(
    name = "num_split",
    srcs = ["num_split.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":hooks",
    ],
)

py_library(
    name = "http",
    srcs = ["http.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":ctx_stack",
        ":exceptions",
        ":i18n",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:site",
        requirement("flask"),
        requirement("pydantic"),
    ],
)

py_library(
    name = "permissions",
    srcs = ["permissions.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":type_defs",
        "//cmk/gui/utils:speaklater",
        "//packages/cmk-ccc:plugin-registry",
    ],
)

py_library(
    name = "user_connection_config_types",
    srcs = ["user_connection_config_types.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":type_defs",
    ],
)

py_library(
    name = "flask_app",
    srcs = ["flask_app.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":features",
        ":http",
        requirement("flask"),
    ],
)

py_library(
    name = "theme",
    srcs = glob(include = ["theme/**/*.py"]),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":ctx_stack",
        ":exceptions",
        ":hooks",
        ":i18n",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
    ],
)

py_library(
    name = "dynamic_icon",
    srcs = ["dynamic_icon.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":theme",
        ":type_defs",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "groups",
    srcs = ["groups.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "figures",
    srcs = ["figures.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
    ],
)

py_library(
    name = "unit_formatter",
    srcs = ["unit_formatter.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("pydantic"),
    ],
)

py_library(
    name = "default_name",
    srcs = ["default_name.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "cert_info",
    srcs = ["cert_info.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:plugin-registry",
    ],
)

py_library(
    name = "ifaceoper",
    srcs = ["ifaceoper.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:i18n",
    ],
)

py_library(
    name = "validate",
    srcs = ["validate.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":exceptions",
        ":i18n",
    ],
)

py_library(
    name = "pseudo_users",
    srcs = ["pseudo_users.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:site",
    ],
)

py_library(
    name = "validation_utils",
    srcs = ["validation_utils.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":exceptions",
        "//packages/cmk-ccc:tty",
        requirement("pydantic"),
    ],
)

py_library(
    name = "single_global_setting",
    srcs = ["single_global_setting.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:store",
    ],
)

py_library(
    name = "ntop",
    srcs = ["ntop.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":hooks",
        ":i18n",
        ":type_defs",
        "//cmk/utils",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:version",
    ],
)

py_library(
    name = "legacy_plugins",
    srcs = ["legacy_plugins.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":log",
        "//cmk/utils",
    ],
)

py_library(
    name = "pdf",
    srcs = ["pdf.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":exceptions",
        ":http",
        ":i18n",
        ":type_defs",
        "//cmk/utils",
        requirement("reportlab"),
    ],
)

py_library(
    name = "job_scheduler_client",
    srcs = ["job_scheduler_client.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":i18n",
        "//cmk/utils",
        "//packages/cmk-ccc:resulttype",
        requirement("requests"),
    ],
)

py_library(
    name = "icons",
    srcs = ["icons.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":i18n",
        ":theme",
        "//cmk/utils",
    ],
)

py_library(
    name = "global_config",
    srcs = ["global_config.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":log",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        requirement("pydantic"),
    ],
)

py_library(
    name = "logged_in",
    srcs = ["logged_in.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":ctx_stack",
        ":exceptions",
        ":hooks",
        ":i18n",
        ":type_defs",
        "//cmk/gui/utils:permission_verification",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:security_log_events",
        "//cmk/gui/utils:selection_id",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "breadcrumb",
    srcs = ["breadcrumb.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:speaklater",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "display_options",
    srcs = ["display_options.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":ctx_stack",
        ":http",
        "//cmk/gui/htmllib:html",
    ],
)

py_library(
    name = "main_menu_types",
    srcs = ["main_menu_types.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":http",
        ":logged_in",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:speaklater",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "color",
    srcs = ["color.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":ctx_stack",
        ":i18n",
        ":type_defs",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/utils:html",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:inventory_ui",
    ],
)

py_library(
    name = "page_menu_entry",
    srcs = ["page_menu_entry.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "page_state",
    srcs = ["page_state.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":type_defs",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/htmllib:type_defs",
        "//cmk/gui/utils:html",
    ],
)

py_library(
    name = "page_menu",
    srcs = ["page_menu.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":breadcrumb",
        ":http",
        ":i18n",
        ":logged_in",
        ":type_defs",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:loading_transition",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:popups",
        "//cmk/gui/utils:selection_id",
        "//cmk/gui/utils:urls",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
    ],
)

py_library(
    name = "main_menu",
    srcs = ["main_menu.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":main_menu_types",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "top_heading",
    srcs = ["top_heading.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":breadcrumb",
        ":http",
        ":i18n",
        ":page_menu",
        ":page_state",
        ":type_defs",
        "//cmk/gui/htmllib:debug_vars",
        "//cmk/gui/htmllib:foldable_container",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:urls",
        "//cmk/utils",
        "//packages/cmk-licensing",
    ],
)

py_library(
    name = "header",
    srcs = ["header.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":breadcrumb",
        ":page_menu",
        ":top_heading",
        "//cmk/gui/htmllib:html",
    ],
)

py_library(
    name = "icon_helpers",
    srcs = ["icon_helpers.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":type_defs",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "search_menu",
    srcs = ["search_menu.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":http",
        ":i18n",
        ":logged_in",
        ":main_menu",
        ":main_menu_types",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "table",
    srcs = ["table.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":http",
        ":i18n",
        ":logged_in",
        ":num_split",
        ":type_defs",
        "//cmk/gui/htmllib:foldable_container",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/htmllib:tag_rendering",
        "//cmk/gui/htmllib:type_defs",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:rendering",
        "//cmk/gui/utils:selection_id",
        "//cmk/gui/utils:urls",
    ],
)

py_library(
    name = "view_utils",
    srcs = ["view_utils.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":http",
        ":i18n",
        ":log",
        ":logged_in",
        ":theme",
        ":type_defs",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:labels",
        "//cmk/gui/utils:loading_transition",
        "//cmk/gui/utils:urls",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
    ],
)

py_library(
    name = "forms",
    srcs = ["forms.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":http",
        ":logged_in",
        ":theme",
        "//cmk/gui/htmllib:foldable_container",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:html",
    ],
)

py_library(
    name = "general_config",
    srcs = ["general_config.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":role_types",
        ":type_defs",
        ":user_connection_config_types",
        "//cmk/checkengine",
        "//cmk/gui/utils:temperate_unit",
        "//cmk/inventory",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
    ],
)

py_library(
    name = "config",
    srcs = ["config.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-dcd:__pkg__",
        "//non-free/packages/cmk-liveproxyd:__pkg__",
        "//non-free/packages/cmk-otel-collector:__pkg__",
        "//non-free/packages/cmk-robotmk:__pkg__",
        "//omd/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":ctx_stack",
        ":exceptions",
        ":general_config",
        ":i18n",
        ":legacy_plugins",
        ":log",
        ":type_defs",
        "//cmk/utils",
    ],
)

py_library(
    name = "crash_handler",
    srcs = ["crash_handler.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":breadcrumb",
        ":header",
        ":http",
        ":i18n",
        ":log",
        ":logged_in",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:mobile",
        "//cmk/gui/utils:urls",
        "//cmk/utils",
        "//packages/cmk-ccc:crash-reporting",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
    ],
)

py_library(
    name = "pages",
    srcs = ["pages.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config",
        ":crash_handler",
        ":ctx_stack",
        ":exceptions",
        ":http",
        ":log",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:json",
    ],
)

py_library(
    name = "cron",
    srcs = ["cron.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config",
    ],
)

py_library(
    name = "agent_commands",
    srcs = ["agent_commands.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config",
        ":logged_in",
        "//cmk/gui/utils:urls",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "default_permissions",
    srcs = ["default_permissions.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config",
        ":i18n",
        ":permissions",
    ],
)

py_library(
    name = "alarm",
    srcs = ["alarm.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":ctx_stack",
        "//cmk/gui/htmllib:html",
    ],
)

py_library(
    name = "query_filters",
    srcs = ["query_filters.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":exceptions",
        ":i18n",
        ":logged_in",
        ":num_split",
        ":type_defs",
        "//cmk/gui/utils:labels",
        "//cmk/gui/utils:user_errors",
        "//cmk/utils",
    ],
)

py_library(
    name = "sites",
    srcs = ["sites.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config",
        ":ctx_stack",
        ":flask_app",
        ":http",
        ":i18n",
        ":log",
        ":logged_in",
        ":site_config",
        "//cmk/gui/utils:compatibility",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-licensing",
        "//packages/cmk-livestatus-client",
    ],
)

py_library(
    name = "user_sites",
    srcs = ["user_sites.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config",
        ":logged_in",
        ":site_config",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
    ],
)

py_library(
    name = "painter_options",
    srcs = ["painter_options.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config",
        ":display_options",
        ":hooks",
        ":http",
        ":i18n",
        ":logged_in",
        ":type_defs",
        ":view_utils",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/valuespec",
    ],
)

py_library(
    name = "customer",
    srcs = ["customer.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":groups",
        ":hooks",
        "//cmk/gui/valuespec",
        "//cmk/utils",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client",
    ],
)

py_library(
    name = "weblib",
    srcs = ["weblib.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config",
        ":exceptions",
        ":http",
        ":i18n",
        ":logged_in",
        ":pages",
        "//cmk/gui/utils:selection_id",
    ],
)

py_library(
    name = "key_mgmt",
    srcs = ["key_mgmt.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":breadcrumb",
        ":config",
        ":exceptions",
        ":http",
        ":i18n",
        ":logged_in",
        ":page_menu",
        ":table",
        ":type_defs",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:csrf_token",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
        "//cmk/gui/valuespec",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-crypto",
        requirement("python-dateutil"),
    ],
)

py_library(
    name = "werks",
    srcs = ["werks.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":breadcrumb",
        ":config",
        ":exceptions",
        ":header",
        ":hooks",
        ":http",
        ":i18n",
        ":logged_in",
        ":main_menu",
        ":num_split",
        ":page_menu",
        ":pages",
        ":table",
        ":type_defs",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/htmllib:tag_rendering",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:flashed_messages",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
        "//cmk/gui/valuespec",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-werks",
    ],
)

py_library(
    name = "product_usage_analytics_popup",
    srcs = ["product_usage_analytics_popup.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config",
        ":http",
        ":log",
        ":logged_in",
        ":site_config",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:product_usage_analytics_popup_cookie",
        "//cmk/gui/utils:urls",
        "//cmk/product_usage",
        "//cmk/utils",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "help",
    srcs = ["help.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":http",
        ":logged_in",
        ":pages",
    ],
)

py_library(
    name = "auth",
    srcs = ["auth.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config",
        ":exceptions",
        ":http",
        ":i18n",
        ":log",
        ":pseudo_users",
        ":site_config",
        ":type_defs",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:htpasswd",
        "//cmk/gui/utils:security_log_events",
        "//cmk/gui/utils:urls",
        "//cmk/utils",
        "//packages/cmk-ccc:user",
        "//packages/cmk-crypto",
    ],
)

py_library(
    name = "session",
    srcs = ["session.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":auth",
        ":config",
        ":exceptions",
        ":i18n",
        ":logged_in",
        ":permissions",
        ":pseudo_users",
        ":type_defs",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:flashed_messages",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:security_log_events",
        "//cmk/gui/wsgi:utils",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        requirement("flask"),
    ],
)

# Monolithic target which we extract smaller targets from. As long as we are in the in place
# extraction process below the cmk.gui module hierarchy, we will have to work with excludes. This
# will be cleaned up when we move the pieces into their future python module structure.
py_library(
    name = "gui",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "agent_commands.py",
            "alarm.py",
            "auth.py",
            "breadcrumb.py",
            "cert_info.py",
            "color.py",
            "config.py",
            "crash_handler.py",
            "cron.py",
            "customer.py",
            "ctx_stack.py",
            "default_permissions.py",
            "default_name.py",
            "display_options.py",
            "dynamic_icon.py",
            "exceptions.py",
            "features.py",
            "figures.py",
            "flask_app.py",
            "forms.py",
            "general_config.py",
            "global_config.py",
            "groups.py",
            "help.py",
            "hooks.py",
            "http.py",
            "i18n.py",
            "icons.py",
            "ifaceoper.py",
            "job_scheduler_client.py",
            "key_mgmt.py",
            "legacy_plugins.py",
            "logged_in.py",
            "header.py",
            "log.py",
            "main_menu.py",
            "main_menu_types.py",
            "ntop.py",
            "num_split.py",
            "page_menu.py",
            "pages.py",
            "icon_helpers.py",
            "page_menu_entry.py",
            "page_state.py",
            "painter_options.py",
            "pdf.py",
            "permissions.py",
            "product_usage_analytics_popup.py",
            "pseudo_users.py",
            "role_types.py",
            "query_filters.py",
            "search_menu.py",
            "session.py",
            "single_global_setting.py",
            "site_config.py",
            "sites.py",
            "table.py",
            "theme/**/*.py",
            "top_heading.py",
            "type_defs.py",
            "unit_formatter.py",
            "user_connection_config_types.py",
            "user_sites.py",
            "validate.py",
            "validation_utils.py",
            "view_utils.py",
            "weblib.py",
            "werks.py",
        ],
    ) + [
        "//cmk/gui/fields:gui_srcs",
        "//cmk/gui/form_specs:gui_srcs",
        "//cmk/gui/nodevis:gui_srcs",
        "//cmk/gui/oauth2_connections:gui_srcs",
        "//cmk/gui/openapi:gui_srcs",
        "//cmk/gui/rule_specs:gui_srcs",
        "//cmk/gui/userdb:gui_srcs",
        "//cmk/gui/wsgi:gui_srcs",
    ],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-dcd:__pkg__",
        "//non-free/packages/cmk-liveproxyd:__pkg__",
        "//non-free/packages/cmk-otel-collector:__pkg__",
        "//non-free/packages/cmk-robotmk:__pkg__",
        "//non-free/packages/cmk-telemetry:__subpackages__",
        "//omd/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":agent_commands",
        ":alarm",
        ":auth",
        ":breadcrumb",
        ":cert_info",
        ":color",
        ":config",
        ":crash_handler",
        ":cron",
        ":ctx_stack",
        ":customer",
        ":default_name",
        ":default_permissions",
        ":display_options",
        ":dynamic_icon",
        ":exceptions",
        ":features",
        ":figures",
        ":flask_app",
        ":forms",
        ":general_config",
        ":global_config",
        ":groups",
        ":header",
        ":help",
        ":hooks",
        ":http",
        ":i18n",
        ":icon_helpers",
        ":icons",
        ":ifaceoper",
        ":job_scheduler_client",
        ":key_mgmt",
        ":legacy_plugins",
        ":log",
        ":logged_in",
        ":main_menu",
        ":main_menu_types",
        ":ntop",
        ":num_split",
        ":page_menu",
        ":page_menu_entry",
        ":page_state",
        ":pages",
        ":painter_options",
        ":pdf",
        ":permissions",
        ":product_usage_analytics_popup",
        ":pseudo_users",
        ":query_filters",
        ":role_types",
        ":search_menu",
        ":session",
        ":single_global_setting",
        ":site_config",
        ":sites",
        ":table",
        ":theme",
        ":top_heading",
        ":type_defs",
        ":unit_formatter",
        ":user_connection_config_types",
        ":user_sites",
        ":validate",
        ":validation_utils",
        ":view_utils",
        ":weblib",
        ":werks",
        "//cmk/automations",
        "//cmk/bi",
        "//cmk/checkengine",
        "//cmk/diagnostics",
        "//cmk/diskspace",
        "//cmk/fields",
        "//cmk/gui/background_job/job",
        "//cmk/gui/fields:base",
        "//cmk/gui/form_specs",
        "//cmk/gui/htmllib:debug_vars",
        "//cmk/gui/htmllib:foldable_container",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/htmllib:tag_rendering",
        "//cmk/gui/htmllib:type_defs",
        "//cmk/gui/nodevis:utils",
        "//cmk/gui/oauth2_connections:watolib_store",
        "//cmk/gui/openapi:restful_objects_type_defs",
        "//cmk/gui/openapi:utils",
        "//cmk/gui/rest_api_types:notifications",
        "//cmk/gui/rule_specs:compatibility",
        "//cmk/gui/rule_specs:loader",
        "//cmk/gui/search",
        "//cmk/gui/search:match_items",
        "//cmk/gui/token_auth",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:agent",
        "//cmk/gui/utils:agent_registration",
        "//cmk/gui/utils:autocompleter_config",
        "//cmk/gui/utils:compatibility",
        "//cmk/gui/utils:confirm_with_preview",
        "//cmk/gui/utils:csrf_token",
        "//cmk/gui/utils:dataclasses",
        "//cmk/gui/utils:encrypter",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:filter",
        "//cmk/gui/utils:flashed_messages",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:htpasswd",
        "//cmk/gui/utils:json",
        "//cmk/gui/utils:labels",
        "//cmk/gui/utils:language_cookie",
        "//cmk/gui/utils:loading_transition",
        "//cmk/gui/utils:misc",
        "//cmk/gui/utils:mobile",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:permission_verification",
        "//cmk/gui/utils:popups",
        "//cmk/gui/utils:product_usage_analytics_popup_cookie",
        "//cmk/gui/utils:regex",
        "//cmk/gui/utils:rendering",
        "//cmk/gui/utils:request_context",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:security_log_events",
        "//cmk/gui/utils:selection_id",
        "//cmk/gui/utils:sort",
        "//cmk/gui/utils:speaklater",
        "//cmk/gui/utils:temperate_unit",
        "//cmk/gui/utils:time",
        "//cmk/gui/utils:timeout_manager",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
        "//cmk/gui/utils:user_errors",
        "//cmk/gui/utils:user_frontend_settings_cookie",
        "//cmk/gui/valuespec",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:groups_io",
        "//cmk/gui/watolib:password_store",
        "//cmk/gui/watolib:passwords",
        "//cmk/gui/watolib:registries",
        "//cmk/gui/watolib:tag_config_file",
        "//cmk/gui/wsgi:utils",
        "//cmk/inventory",
        "//cmk/piggyback:backend",
        "//cmk/piggyback:hub",
        "//cmk/plugins",
        "//cmk/product_usage",
        "//cmk/rrd",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:archive",
        "//packages/cmk-ccc:cleanup",
        "//packages/cmk-ccc:config-path",
        "//packages/cmk-ccc:cpu-tracking",
        "//packages/cmk-ccc:crash-reporting",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:profile",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:timeout",
        "//packages/cmk-ccc:translations",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-crypto",
        "//packages/cmk-ec",
        "//packages/cmk-ec:event",
        "//packages/cmk-ec:syslog",
        "//packages/cmk-events",
        "//packages/cmk-licensing",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//packages/cmk-messaging",
        "//packages/cmk-mkp-tool",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:inventory_ui",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugins:aws",
        "//packages/cmk-plugins:lib",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//packages/cmk-trace",
        "//packages/cmk-werks",
        requirement("apispec"),
        requirement("apispec-oneofschema"),
        requirement("cryptography"),
        requirement("docstring-parser"),
        requirement("fastapi"),
        requirement("fido2"),
        requirement("flask"),
        requirement("jinja2"),
        requirement("marshmallow"),
        requirement("marshmallow-oneofschema"),
        requirement("openapi-spec-validator"),
        requirement("icalendar"),
        requirement("opentelemetry-api"),
        requirement("opentelemetry-instrumentation-fastapi"),
        requirement("opentelemetry-instrumentation-redis"),
        requirement("opentelemetry-instrumentation-requests"),
        requirement("opentelemetry-instrumentation-wsgi"),
        requirement("opentelemetry-sdk"),
        requirement("pydantic"),
        requirement("pyprof2calltree"),
        requirement("pyparsing"),
        requirement("python-active-directory"),
        requirement("python-dateutil"),
        requirement("python-ldap"),
        requirement("pyyaml"),
        requirement("recurring_ical_events"),
        requirement("redis"),
        requirement("reportlab"),
        requirement("requests"),
        requirement("setproctitle"),
        requirement("uvicorn"),
        requirement("werkzeug"),
    ],
)
