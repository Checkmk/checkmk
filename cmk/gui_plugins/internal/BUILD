load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "internal",
    srcs = ["feature_registration.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:general_pages",
        "//cmk/gui/graphing",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/sidebar",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//packages/cmk-ccc:version",
        "//packages/cmk-licensing",
    ],
)
