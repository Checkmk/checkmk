load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "lib",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//tests:__subpackages__",
    ],
    deps = [
        # WATCH OUT: be careful when adding dependencies here.
        # They will all be part of the bazel sandbox, if an edition
        # stopped shipping them, they would still be there.
        # That would defeat the purpose of this test suite.
        # We can safely assume we won't have a checkmk edition without
        # ruleset matcher or plugin APIs, though.
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-ruleset-matcher",
    ],
)
