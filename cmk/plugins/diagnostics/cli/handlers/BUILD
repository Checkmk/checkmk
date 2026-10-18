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
        "//cmk/base:diagnostics",
        "//cmk/config",
        "//cmk/plugins/diagnostics/cli",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-diagnostics:engine",
        "//packages/cmk-plugin-apis:cli",
        "//packages/cmk-plugin-apis:diagnostics",
    ],
)
