load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "commands",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:exceptions",
        "//cmk/gui:logged_in",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-livestatus-client:py_livestatus",
    ],
)
