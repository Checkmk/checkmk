load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "configlib",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
        "//cmk/config_anonymizer:__pkg__",
        "//non-free/packages/cmk-bakery:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/base/default_config:default-config",
        "//cmk/checkengine",
        "//cmk/piggyback:backend",
        "//cmk/rrd",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:translations",
        "//packages/cmk-check-engine:fetchers",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-logwatch:config",
        "//packages/cmk-plugin-apis:agent_based",
    ],
)
