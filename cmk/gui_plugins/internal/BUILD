load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "internal",
    srcs = ["feature_registration.py"],
    imports = ["../../.."],
    tags = [
        "deballast-keep=//packages/cmk-licensing:cmk-licensing",  # transitively provides the imported cmk.licensing.basics.options (basics/ is a separate, non-visible package)
    ],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:page_toolkit",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/pagetypes",
        "//cmk/gui/sidebar",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//packages/cmk-ccc:version",
        "//packages/cmk-licensing",
    ],
)
