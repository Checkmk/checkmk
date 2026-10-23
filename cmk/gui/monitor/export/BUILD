load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "export",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:page_toolkit",
        "//packages/cmk-web/cmk/web/utils",
    ],
)
