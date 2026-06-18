load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "core",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["nagios/_host_check_template.py"],
    ),
    imports = ["../../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        "//cmk/base:config",
        "//cmk/base/configlib",
        "//cmk/core_client",
        "//cmk/utils",
        "//packages/cmk-ccc:config-path",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:checker-plugin",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-check-engine/cmk/checkengine/plugin_backend",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-trace",
    ],
)

py_library(
    name = "host-check-template",
    srcs = ["nagios/_host_check_template.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        ":core",
        "//cmk/base:app",
        "//cmk/base:config",
        "//cmk/base/modes",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:config-path",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine/cmk/checkengine/plugin_backend",
        "//packages/cmk-plugin-apis:discover_plugins",
    ],
)
