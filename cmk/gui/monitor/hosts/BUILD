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
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:api_config",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/pagetypes",
        "//cmk/gui/utils:permission_verification",
        "//cmk/gui/views:command",
    ],
)
