load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files([
    ".f12",
    "openapi/.f12",
    "openapi/spec/spec_generator/generate_api_spec.py",
    "wsgi/.f12",
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
    name = "page_menu_entry",
    srcs = ["page_menu_entry.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
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
            "cert_info.py",
            "ctx_stack.py",
            "default_name.py",
            "dynamic_icon.py",
            "exceptions.py",
            "features.py",
            "figures.py",
            "flask_app.py",
            "global_config.py",
            "groups.py",
            "hooks.py",
            "http.py",
            "i18n.py",
            "icons.py",
            "ifaceoper.py",
            "job_scheduler_client.py",
            "legacy_plugins.py",
            "logged_in.py",
            "log.py",
            "ntop.py",
            "num_split.py",
            "page_menu_entry.py",
            "pdf.py",
            "permissions.py",
            "pseudo_users.py",
            "role_types.py",
            "single_global_setting.py",
            "site_config.py",
            "theme/**/*.py",
            "type_defs.py",
            "unit_formatter.py",
            "user_connection_config_types.py",
            "validate.py",
            "validation_utils.py",
        ],
    ) + [
        "wsgi/applications/index.wsgi",
    ],
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
        ":cert_info",
        ":ctx_stack",
        ":default_name",
        ":dynamic_icon",
        ":exceptions",
        ":features",
        ":figures",
        ":flask_app",
        ":global_config",
        ":groups",
        ":hooks",
        ":http",
        ":i18n",
        ":icons",
        ":ifaceoper",
        ":job_scheduler_client",
        ":legacy_plugins",
        ":log",
        ":logged_in",
        ":ntop",
        ":num_split",
        ":page_menu_entry",
        ":pdf",
        ":permissions",
        ":pseudo_users",
        ":role_types",
        ":single_global_setting",
        ":site_config",
        ":theme",
        ":type_defs",
        ":unit_formatter",
        ":user_connection_config_types",
        ":validate",
        ":validation_utils",
        "//cmk/automations",
        "//cmk/bi",
        "//cmk/checkengine",
        "//cmk/diagnostics",
        "//cmk/diskspace",
        "//cmk/fields",
        "//cmk/gui/htmllib:debug_vars",
        "//cmk/gui/htmllib:foldable_container",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/htmllib:tag_rendering",
        "//cmk/gui/htmllib:type_defs",
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

py_binary(
    name = "generate_api_spec",
    srcs = ["openapi/spec/spec_generator/generate_api_spec.py"],
    main = "openapi/spec/spec_generator/generate_api_spec.py",
    visibility = ["//:__subpackages__"],
    deps = select({
        "@cmk//edition:cloud": [
            "//cmk/editions:community",
            "//cmk/editions/nonfree:cloud",
            "//cmk/editions/nonfree:pro",
            "//cmk/editions/nonfree:ultimate",
        ],
        "@cmk//edition:community": [
            "//cmk/editions:community",
        ],
        "@cmk//edition:pro": [
            "//cmk/editions:community",
            "//cmk/editions/nonfree:pro",
        ],
        "@cmk//edition:ultimate": [
            "//cmk/editions:community",
            "//cmk/editions/nonfree:pro",
            "//cmk/editions/nonfree:ultimate",
        ],
        "@cmk//edition:ultimatemt": [
            "//cmk/editions:community",
            "//cmk/editions/nonfree:pro",
            "//cmk/editions/nonfree:ultimate",
            "//cmk/editions/nonfree:ultimatemt",
        ],
    }) + [
        requirement("pyyaml"),
    ],
)

# Variant of generate_api_spec that always includes at least pro edition
# modules. Used to generate the internal OpenAPI spec for TypeScript types
# consumed by cmk-frontend-vue, which ships the same bundle for all editions.
# Limited to community + pro to avoid pulling in ultimate deps that are not
# available in all nonfree edition checkouts (e.g. pro builds strip ultimate/).
py_binary(
    name = "generate_api_spec_all_editions",
    srcs = ["openapi/spec/spec_generator/generate_api_spec.py"],
    main = "openapi/spec/spec_generator/generate_api_spec.py",
    visibility = ["//:__subpackages__"],
    deps = select({
        "@//:gpl+nonfree_repo": [
            "//cmk/editions:community",
            "//cmk/editions/nonfree:pro",
        ],
        "@//:gpl_repo": [
            "//cmk/editions:community",
        ],
    }) + [
        requirement("pyyaml"),
    ],
)
