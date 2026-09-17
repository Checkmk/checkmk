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
        "//cmk/base:base-app",
        "//cmk/base/automations",
        "//cmk/base/config",
        "//cmk/base/modes",
        "//cmk/cli/engine",
        "//cmk/piggyback:backend",
        "//cmk/utils",
        "//cmk/utils:man_pages",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-licensing/cmk/licensing/basics",
        "//packages/cmk-plugin-apis:cli",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-profiling:backend",
        "//packages/cmk-ruleset-matcher",
        "//packages/cmk-trace",
    ],
)
