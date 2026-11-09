load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "handlers",
    srcs = glob(["*.py"]),
    imports = ["../../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/automations",
        "//cmk/base:notify",
        "//cmk/base/config",
        "//cmk/plugins/notifications/cli",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-plugin-apis:cli",
    ],
)
