load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "router",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/monitor/hosts",
        "//cmk/gui/search/spec",
        "//packages/cmk-ruleset-matcher",
    ],
)
