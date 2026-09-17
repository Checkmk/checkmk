load("@aspect_rules_py//py:defs.bzl", "py_library")

# The "cmk" commands of the diagnostics family, discovered at runtime via
# discover_all_plugins(). They drive the dump engine in cmk.base.diagnostics,
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
        "//cmk/base:diagnostics",
        "//cmk/base/automations",
        "//cmk/cli/engine",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-diagnostics:engine",
        "//packages/cmk-plugin-apis:cli",
        "//packages/cmk-plugin-apis:diagnostics",
    ],
)
