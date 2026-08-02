load("@aspect_rules_py//py:defs.bzl", "py_library")
load("//bazel/rules:doctest.bzl", "py_doc_test")

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
        "//packages/cmk-livestatus-client",
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
    name = "checkers",
    srcs = ["checkers.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        "//cmk/base/config",
        "//cmk/base/errorhandling",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:cpu-tracking",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-check-engine:checker-plugin",
        "//packages/cmk-check-engine:fetcher-protocol",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine:helper-interface",
        "//packages/cmk-check-engine:lib",
        "//packages/cmk-check-engine:section-parser",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-check-engine:sources",
        "//packages/cmk-check-engine:specs",
        "//packages/cmk-check-engine/cmk/checkengine/checking",
        "//packages/cmk-check-engine/cmk/checkengine/discovery",
        "//packages/cmk-check-engine/cmk/checkengine/parser",
        "//packages/cmk-check-engine/cmk/checkengine/plugin_backend",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-livestatus-client",
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
        "//cmk/base/config",
        "//cmk/base/configlib",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-check-engine:checker-plugin",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine:helper-interface",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-check-engine:sources",
        "//packages/cmk-check-engine:specs",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
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
        "//cmk/base/config",
        "//cmk/base/configlib",
        "//cmk/base/core",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-licensing",
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
        ":events",
        "//cmk/automations",
        "//cmk/base/automations",
        "//cmk/base/config",
        "//cmk/base/modes:modes-registry",
        "//cmk/utils",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:timeout",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-events",
        "//packages/cmk-livestatus-client",
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
        "//cmk/automations",
        "//cmk/base/automations",
        "//cmk/base/modes:modes-registry",
        "//cmk/utils",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-diagnostics:engine",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-plugin-apis:diagnostics",
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
    tags = [
        "deballast-keep=//cmk/base:diagnostics",  # loaded at runtime via discover_modes()
        "deballast-keep=//cmk/base:localize",  # loaded at runtime via discover_modes()
        "deballast-keep=//cmk/base:notify",  # loaded at runtime via discover_modes()
        "deballast-keep=//cmk/base/automations:automations",  # loaded at runtime via discover_automations()
        "deballast-keep=//cmk/base/modes:modes",  # loaded at runtime via discover_modes()
        "deballast-keep=//cmk/base/modes:modes-registry",  # provides discover_modes()/Modes for CLI assembly
    ],
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
        "//cmk/utils:paths",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-licensing",
    ],
)

py_library(
    name = "app",
    srcs = ["app.py"],
    imports = ["../.."],
    visibility = [
        "//bin:__subpackages__",
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
        "//cmk/base/config",
        "//cmk/base/configlib",
        "//cmk/base/core",
        "//cmk/base/errorhandling",
        "//cmk/base/modes",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:config-path",
        "//packages/cmk-ccc:cpu-tracking",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine:inventory",
        "//packages/cmk-check-engine:specs",
        "//packages/cmk-check-engine/cmk/checkengine/checking",
        "//packages/cmk-check-engine/cmk/checkengine/parser",
        "//packages/cmk-check-engine/cmk/checkengine/plugin_backend",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
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
        ":diagnostics",
        ":dump-host",
        ":events",
        ":localize",
        ":notify",
        ":parent-scan",
        "//cmk/base/api",
        "//cmk/base/automation_helper:automation-helper",
        "//cmk/base/automations",
        "//cmk/base/config",
        "//cmk/base/configlib",
        "//cmk/base/core",
        "//cmk/base/core:host-check-template",
        "//cmk/base/default_config:default-config",
        "//cmk/base/errorhandling",
        "//cmk/base/modes",
        "//cmk/base/modes:main",
        "//cmk/base/modes:modes-registry",
        "//cmk/base/plugins:plugins-bakery",
        "//packages/cmk-check-engine:sources",
    ],
)

sh_library(
    name = "f12",
    srcs = [
        ".f12",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        ":diagnostics",
        ":notify",
    ],
)
