load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "shared_endpoint_families",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/openapi/restful_objects",
    ],
)
