load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files([".f12"])

py_library(
    name = "utils",
    srcs = [
        "profiling.py",
        "utils.py",
    ],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
    ],
)

py_library(
    name = "events",
    srcs = ["events.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:daemon",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:site",
        "//packages/cmk-events",
        "//packages/cmk-livestatus-client:py_livestatus",
    ],
)

py_library(
    name = "parent-scan",
    srcs = ["parent_scan.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        "//cmk/automations",
        "//cmk/utils",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:tty",
    ],
)

py_library(
    name = "snmp-plugin-store",
    srcs = ["snmp_plugin_store.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        "//cmk/checkengine",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine:snmplib",
    ],
)

py_library(
    name = "config",
    srcs = ["config.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":parent-scan",
        ":snmp-plugin-store",
        "//cmk/base/configlib",
        "//cmk/base/default_config:default-config",
        "//cmk/base/sources",
        "//cmk/checkengine",
        "//cmk/inventory",
        "//cmk/piggyback:backend",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine:helper-interface",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-trace",
    ],
)

py_library(
    name = "checkers",
    srcs = ["checkers.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        ":config",
        "//cmk/base/errorhandling",
        "//cmk/base/sources",
        "//cmk/checkengine",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:cpu-tracking",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine:helper-interface",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//packages/cmk-plugin-apis:agent_based",
    ],
)

py_library(
    name = "dump-host",
    srcs = ["dump_host.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        ":config",
        "//cmk/base/configlib",
        "//cmk/base/sources",
        "//cmk/checkengine",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine:helper-interface",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-plugin-apis:password_store",
    ],
)

py_library(
    name = "base-app",
    srcs = ["base_app.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
        "//cmk/config_anonymizer:__pkg__",
        "//non-free/packages/cmk-bakery:__pkg__",
    ],
    deps = [
        ":config",
        "//cmk/base/automations",
        "//cmk/base/configlib",
        "//cmk/base/core",
        "//cmk/base/modes:modes-registry",
        "//cmk/checkengine",
        "//cmk/utils",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine:helper-interface",
    ],
)

py_library(
    name = "notify",
    srcs = ["notify.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":base-app",
        ":config",
        ":events",
        ":utils",
        "//cmk/automations",
        "//cmk/base/automations",
        "//cmk/base/modes:modes-registry",
        "//cmk/checkengine",
        "//cmk/utils",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:timeout",
        "//packages/cmk-ccc:version",
        "//packages/cmk-events",
        "//packages/cmk-livestatus-client:py_livestatus",
    ],
)

py_library(
    name = "diagnostics",
    srcs = ["diagnostics.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":base-app",
        ":config",
        "//cmk/automations",
        "//cmk/base/automations",
        "//cmk/base/configlib",
        "//cmk/base/modes:modes-registry",
        "//cmk/checkengine",
        "//cmk/diagnostics",
        "//cmk/inventory",
        "//cmk/utils",
        "//packages/cmk-ccc:crash-reporting",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client:py_livestatus",
        requirement("requests"),
    ],
)

py_library(
    name = "localize",
    srcs = ["localize.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        ":base-app",
        "//cmk/base/modes:modes-registry",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:tty",
    ],
)

py_library(
    name = "community-app",
    srcs = ["community_app.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        ":base-app",
        ":diagnostics",
        ":localize",
        ":notify",
        "//cmk/base/automations",
        "//cmk/base/core",
        "//cmk/base/modes",
        "//cmk/base/modes:modes-registry",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:fetchers",
    ],
)

py_library(
    name = "app",
    srcs = ["app.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
        "//cmk/config_anonymizer:__pkg__",
        "//cmk/product_usage:__pkg__",
        "//cmk/update_config:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":base-app",
        ":community-app",
        "//packages/cmk-ccc:version",
    ],
)

py_library(
    name = "check-cmk-inv",
    srcs = ["check_cmk_inv.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        ":app",
        ":base-app",
        ":checkers",
        ":config",
        "//cmk/base/configlib",
        "//cmk/base/core",
        "//cmk/base/errorhandling",
        "//cmk/base/modes",
        "//cmk/checkengine",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:config-path",
        "//packages/cmk-ccc:cpu-tracking",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-plugin-apis:discover_plugins",
    ],
)

py_library(
    name = "base",
    srcs = [],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":app",
        ":base-app",
        ":check-cmk-inv",
        ":checkers",
        ":community-app",
        ":config",
        ":diagnostics",
        ":dump-host",
        ":events",
        ":localize",
        ":notify",
        ":parent-scan",
        ":snmp-plugin-store",
        ":utils",
        "//cmk/base/api",
        "//cmk/base/automation_helper:automation-helper",
        "//cmk/base/automations",
        "//cmk/base/configlib",
        "//cmk/base/core",
        "//cmk/base/core:host-check-template",
        "//cmk/base/default_config:default-config",
        "//cmk/base/errorhandling",
        "//cmk/base/modes",
        "//cmk/base/modes:modes-registry",
        "//cmk/base/plugins:plugins-bakery",
        "//cmk/base/sources",
    ],
)
