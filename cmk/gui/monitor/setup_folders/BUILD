load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "setup_folders",
    srcs = ["__init__.py"],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:core_toolkit",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-ruleset-matcher",
    ],
)
