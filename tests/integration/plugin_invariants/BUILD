load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

# Every test here checks a property that each plug-in (or other shipped
# element) must have on its own. If it holds for the union of all editions,
# it holds for each of them, so the tests run once against everything we
# ship (see nonfree/BUILD). Tests that depend on what a particular edition
# ships belong to plugin_consistency or edition_scope.

py_library(
    name = "plugin_invariants",
    testonly = True,
    srcs = glob(["*.py"]),
    imports = ["../../.."],
    visibility = ["//tests/integration/plugin_invariants:__subpackages__"],
    deps = [
        "//cmk/gui/graphing",
        "//cmk/plugins",
        "//cmk/server_side_calls_backend",
        "//cmk/utils:man_pages",
        "//packages/cmk-ccc:version",
        "//packages/cmk-check-engine/cmk/checkengine/plugin_backend",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugins:all_families",
        "//tests/code_quality:bazel_utils",
        requirement("pytest"),
    ],
)

# The community repository has no non-free code, so it needs its own target.
py_cmk_test(
    name = "community",
    srcs = [],
    deps = [
        ":plugin_invariants",
        "//:pyproject-toml",
        "//cmk/editions:community",
    ],
)
