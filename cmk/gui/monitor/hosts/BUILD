load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "hosts",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:customer",
        "//cmk/gui/monitor/command",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/pagetypes",
        "//cmk/gui/utils:middle",
        "//cmk/gui/views:components",
        "//packages/cmk-ruleset-matcher",
        "//packages/cmk-web/cmk/web/utils",
    ],
)
