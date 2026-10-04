load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "automations",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
        "//cmk/plugins:__subpackages__",
        "//non-free/packages/cmk-bakery:__pkg__",
        "//non-free/packages/cmk-plugins-nonfree/cmk/plugins/notifications:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/base:app",
        "//cmk/base:base-app",
        "//cmk/base/config",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:timeout",
        "//packages/cmk-inventory:inventory",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-plugin-apis:automations",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-trace",
    ],
)
