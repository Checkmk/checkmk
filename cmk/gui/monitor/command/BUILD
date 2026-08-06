load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "command",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui/utils:base",
        "//packages/cmk-ccc:plugin-registry",
    ],
)
