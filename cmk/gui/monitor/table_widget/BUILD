load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "table_widget",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui/openapi/framework:types",
        "//packages/cmk-web/cmk/web/utils",
        requirement("pydantic"),
    ],
)
