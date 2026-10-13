load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "services",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/monitor/command",
        "//cmk/gui/monitor/hosts",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/pagetypes",
        "//cmk/gui/utils:middle",
        "//cmk/gui/views:components",
        "//packages/cmk-web/cmk/web/utils",
    ],
)
