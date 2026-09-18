load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "cli",
    srcs = ["cli.py"],
    imports = ["../.."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk/gui/search:index",
        "//cmk/utils",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-ec",
        "//packages/cmk-mkp-tool",
        "//packages/cmk-plugin-apis:discover_plugins",
    ],
)
