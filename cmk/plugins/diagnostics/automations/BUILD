load("@aspect_rules_py//py:defs.bzl", "py_library")

# The automations of the diagnostics family, discovered at runtime via
# discover_all_plugins(). They drive the dump engine in cmk.base.diagnostics,
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
        "//cmk/base:diagnostics",
        "//cmk/utils",
        "//cmk/utils:paths",
        "//packages/cmk-diagnostics:automation_types",
        "//packages/cmk-diagnostics:engine",
        "//packages/cmk-plugin-apis:automations",
    ],
)
