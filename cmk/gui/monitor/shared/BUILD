load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "shared",
    srcs = glob(include = ["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
        requirement("annotated-types"),
        requirement("pydantic"),
    ],
)
