load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "api",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
        "//non-free/packages/cmk-bakery:__pkg__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-plugin-apis:bakery",
    ],
)
