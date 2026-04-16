load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "data_source",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:display_options",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:sites",
        "//cmk/gui:type_defs",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/painter:v0_base",
        "//cmk/gui/visuals",
        "//cmk/utils",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-livestatus-client",
    ],
)
