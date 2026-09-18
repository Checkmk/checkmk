load("@aspect_rules_py//py:defs.bzl", "py_library")

# The "cmk" commands of the checkmk family, discovered at runtime via
# discover_all_plugins(). They are tightly coupled to cmk.base, which is why
# they live here and not in //cmk/plugins.
py_library(
    name = "cli",
    srcs = glob(["*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-plugin-apis:cli",
    ],
)
