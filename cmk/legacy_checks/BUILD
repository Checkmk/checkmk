load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "legacy_checks",
    srcs = glob(
        ["**/*.py"],
        allow_empty = True,  # all legacy checks have been migrated
    ),
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/editions:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/plugins",
        "//packages/cmk-plugin-apis:agent_based",
    ],
)
