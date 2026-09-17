load("@aspect_rules_py//py:defs.bzl", "py_library")

# The "cmk" commands of the notifications family, discovered at runtime via
# discover_all_plugins(). They drive the notification engine in cmk.base.notify,
# which is why they are not part of //cmk/plugins.
py_library(
    name = "cli",
    srcs = glob(["*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/automations",
        "//cmk/base:base-app",
        "//cmk/base:notify",
        "//cmk/base/config",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-plugin-apis:cli",
    ],
)
