load("@aspect_rules_py//py:defs.bzl", "py_library")

# The "cmk" commands of the diagnostics family, discovered at runtime via
# discover_all_plugins().
py_library(
    name = "cli",
    srcs = glob(["*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-plugin-apis:cli",
        "//packages/cmk-plugin-apis:diagnostics",
    ],
)
