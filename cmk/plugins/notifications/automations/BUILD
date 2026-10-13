load("@aspect_rules_py//py:defs.bzl", "py_library")

# The automations of the notifications family, discovered at runtime via
# discover_all_plugins(). They drive the notification engine in cmk.base.notify,
# which is why they are not part of //cmk/plugins.
py_library(
    name = "automations",
    srcs = glob(["*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/automations",
        "//cmk/base:notify",
        "//cmk/base/automations",
        "//cmk/utils",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-plugin-apis:automations",
    ],
)
