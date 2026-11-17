load("@aspect_rules_py//py:defs.bzl", "py_library")

# The "cmk" commands of the checkmk family, discovered at runtime via
# discover_all_plugins().
py_library(
    name = "cli",
    srcs = glob(["*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-plugins-nonfree:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine:snmplib",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-plugin-apis:cli",
        "//packages/cmk-ruleset-matcher",
    ],
)
